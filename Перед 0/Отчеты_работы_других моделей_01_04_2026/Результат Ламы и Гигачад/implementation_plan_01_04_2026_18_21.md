# Accuracy Benchmarking: Llama 70B vs GigaChat

The goal is to provide a comprehensive accuracy comparison between Llama 70B and GigaChat (and potentially other models) using the established benchmark framework.

## Proposed Steps

1. **Complete Llama 70B Benchmark**:
   - Continue monitoring the current background process (`adc64e48-e0ec-47e7-bd34-107ea820b0e4`).
   - Ensure `ab_benchmark_results.json` is generated with full results for Packages 1, 2, and 4.

2. **Configure GigaChat Benchmark**:
   - Create a separate config or environment for GigaChat (`config_gigachat.yaml`).
   - Verify GigaChat API access (based on `Настройка GigaChat.docx`).
   - *Note*: If GigaChat is hosted on the same LM Studio server as Llama, I will need to ask the user to switch models manually.

3. **Run GigaChat Benchmark**:
   - Run the `ab_benchmark.py` script (or a modified version) using the GigaChat model.
   - Save results to `ab_benchmark_gigachat_results.json`.

4. **Consolidate and Compare**:
   - Extract metrics (Title, Customer, Developer, Year, DocType accuracy) for both models.
   - Include comparison with other available reports (GPT-OSS from existing TSVs).
   - Generate a final `benchmark_comparison_report.md` with tables and charts.

## User Review Required

> [!IMPORTANT]
> **Model Switching**: If you are using LM Studio to host the models, I can only run one at a time. After Llama 70B finishes, I will need you to load **gigachat3.1-10b-a1.8b** in LM Studio so I can start its benchmark.

## Verification Plan

- Check JSON result files for completeness.
- Compare scores across the same file sets.
- Verify that the matching logic (File -> Etalon) is consistent for both models.
