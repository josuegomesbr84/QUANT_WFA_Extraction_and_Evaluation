import asyncio
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

from scraper.auth import login
from scraper.upload import send_wfa
from scraper.extractor import (
    get_wfm,
    get_scenario_labels,
    select_scenario,
    get_scenario_data,
    get_chart_data,
)
from analysis.metrics import compute_all_metrics
from analysis.verdict import calcular_veredicto, veredicto_global
from output.json_writer import save as save_json
from output.html_report import save as save_html


def parse_args():
    parser = argparse.ArgumentParser(
        description="Extrator e avaliador automático de resultados WFA — BotSpot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python main.py --wfa "C:/path/DQWFA_52875702.wfa"
  python main.py --wfa "C:/path/DQWFA_52875702.wfa" --email user@email.com --password "senha"
  python main.py --wfa "C:/path/DQWFA_52875702.wfa" --headed
        """,
    )
    parser.add_argument("--wfa", required=True, help="Caminho para o arquivo .wfa")
    parser.add_argument("--email", default=None, help="E-mail do BotSpot (ou use .env)")
    parser.add_argument("--password", default=None, help="Senha do BotSpot (ou use .env)")
    parser.add_argument("--headed", action="store_true", help="Exibe o browser durante a execução")
    parser.add_argument("--output-dir", default="resultados", help="Pasta para salvar os arquivos de saída")
    return parser.parse_args()


async def run(wfa_path: str, email: str, password: str, headed: bool, output_dir: str) -> dict:
    print(f"\n{'='*55}")
    print(f"  WFA Extractor — BotSpot")
    print(f"  Arquivo: {Path(wfa_path).name}")
    print(f"{'='*55}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # 1. Login
        print("[1/4] Fazendo login no BotSpot...")
        await login(page, email, password)
        print("      ✓ Login realizado")

        # 2. Upload
        print("[2/4] Enviando arquivo .wfa...")
        await send_wfa(page, wfa_path)
        print("      ✓ Upload concluído — /wfareport habilitado")

        # 3. WFM
        print("[3/4] Extraindo Walk Forward Matrix...")
        wfm = await get_wfm(page)
        print(f"      ✓ {len(wfm)} cenários na WFM")

        # 4. Iteração pelos cenários
        print("[4/4] Processando cenários:")
        labels = await get_scenario_labels(page)
        n = len(labels)

        cenarios = []
        for i in range(n):
            label = labels[i]
            print(f"      [{i + 1:02d}/{n}] {label}", end=" ... ")

            option_text = await select_scenario(page, i)
            scenario_data = await get_scenario_data(page)
            chart_data = await get_chart_data(page)

            meses_total = 0
            try:
                raw = scenario_data["cards"].get("meses") or "0"
                meses_total = int(str(raw).strip())
            except (ValueError, TypeError):
                pass

            metrics = compute_all_metrics(scenario_data, meses_total)
            verdict = calcular_veredicto(metrics)

            simbolo = {"APROVADO": "✅", "ATENÇÃO": "⚠️", "REPROVADO": "❌"}.get(verdict["veredicto"], "—")
            print(f"{simbolo} {verdict['veredicto']} ({verdict['total']}/100 pts)")

            cenarios.append({
                "indice": i,
                "label": option_text,
                "cards": scenario_data["cards"],
                "zscore_raw": scenario_data.get("zscore_raw"),
                "tabela_wfa": scenario_data["tabela_wfa"],
                "parametros_frequentes": scenario_data["parametros_frequentes"],
                "charts": chart_data,
                "metrics": metrics,
                "veredicto": verdict,
            })

        await browser.close()

    v_global = veredicto_global(cenarios)

    result = {
        "arquivo_wfa": Path(wfa_path).name,
        "veredicto_global": v_global,
        "wfm": wfm,
        "cenarios": cenarios,
    }

    json_path = save_json(result, output_dir)
    html_path = save_html(result, output_dir)

    simbolo_g = {"APROVADO": "✅", "ATENÇÃO": "⚠️", "REPROVADO": "❌"}.get(v_global, "—")
    print(f"\n{'='*55}")
    print(f"  {simbolo_g}  Veredicto Global: {v_global}")
    print(f"{'='*55}")
    print(f"\n  JSON  → {json_path}")
    print(f"  HTML  → {html_path}\n")

    return result


def main():
    load_dotenv()
    args = parse_args()

    email = args.email or os.getenv("BOTSPOT_EMAIL")
    password = args.password or os.getenv("BOTSPOT_PASSWORD")

    if not email or not password:
        print("\nErro: credenciais não encontradas.")
        print("  Use --email e --password, ou crie um arquivo .env com:")
        print("    BOTSPOT_EMAIL=seu@email.com")
        print("    BOTSPOT_PASSWORD=sua_senha\n")
        sys.exit(1)

    if not Path(args.wfa).exists():
        print(f"\nErro: arquivo não encontrado: {args.wfa}\n")
        sys.exit(1)

    asyncio.run(run(args.wfa, email, password, args.headed, args.output_dir))


if __name__ == "__main__":
    main()
