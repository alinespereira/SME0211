"""Testes de `printing_company.settings`: leitura do `.env` e prioridade
das variáveis de ambiente."""

# O BaseSettings aceita `_env_file` no construtor, mas o pyright só vê os
# campos declarados e reclamaria aqui.
# pyright: reportCallIssue=false

from pathlib import Path

import pytest

from printing_company.settings import ENV_FILE, ROOT_DIR, Settings


@pytest.fixture(autouse=True)
def _clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tira do ambiente as variáveis dos campos, para os testes não
    dependerem do terminal de quem roda."""
    for name in ("SHIFT_HOURS", "ENERGY_PRICE"):
        monkeypatch.delenv(name, raising=False)


def test_defaults_without_env_file() -> None:
    settings = Settings(_env_file=None)
    assert settings.shift_hours == 10.0
    assert settings.energy_price == 0.86


def test_reads_env_file(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("SHIFT_HOURS=8\nenergy_price=1.2\nOUTRA=ignorada\n")
    settings = Settings(_env_file=env)
    assert settings.shift_hours == 8.0
    assert settings.energy_price == 1.2


def test_environment_wins_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / ".env"
    env.write_text("SHIFT_HOURS=8\n")
    monkeypatch.setenv("SHIFT_HOURS", "12")
    assert Settings(_env_file=env).shift_hours == 12.0


def test_env_example_has_paper_values() -> None:
    """O `.env.example` versionado tem os valores padrão do artigo."""
    example = Settings(_env_file=ROOT_DIR / ".env.example")
    assert example.shift_hours == Settings(_env_file=None).shift_hours
    assert example.energy_price == Settings(_env_file=None).energy_price


def test_env_file_is_at_project_root() -> None:
    assert ENV_FILE == ROOT_DIR / ".env"
