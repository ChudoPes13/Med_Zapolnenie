# МедЖарвис

Локальный production-oriented MVP ассистента качества приема: realtime ЭМК, VAD-сегменты, финальная суммаризация, профильные проверки для нижних конечностей и стоматологии при явном стоматологическом контексте.

## Быстрый старт

```powershell
scripts\setup.ps1
scripts\download_model.ps1 -Profile qwen3-4b
scripts\download_asr.ps1
scripts\start_medjarvis.ps1 -Restart
```

Backend: http://127.0.0.1:8000  
Frontend: http://127.0.0.1:5173

Сервис рассчитан на Windows 11, RTX 3070 8GB, Python 3.12, CUDA 13.x и локальный `llama-server`.
`scripts\start_medjarvis.ps1 -Restart` поднимает `llama-server`, backend и frontend; после изменения кода используйте `-Restart`, чтобы не остался старый backend на 8000.

Правила обработки диалогов: [docs/DIALOG_PROCESSING.md](docs/DIALOG_PROCESSING.md)
