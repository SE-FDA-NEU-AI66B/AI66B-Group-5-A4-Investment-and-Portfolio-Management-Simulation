"""deploy/gcp/setup.sh keeps the VM's settings on every re-run (#163)."""

from pathlib import Path

SETUP = (Path(__file__).resolve().parents[1] / 'deploy' / 'gcp' / 'setup.sh').read_text()


def test_settings_file_is_checked_with_sudo_so_updates_keep_it():
    # /etc/virtutrade is 750 root:virtutrade: without sudo the file looks missing
    # and the template overwrites QUOTE_MODE, DATABASE_PATH and SECRET_KEY.
    assert 'if ! sudo test -f "$ENV_FILE"; then' in SETUP
    assert '[ ! -f "$ENV_FILE" ]' not in SETUP


def test_every_run_records_the_deployed_commit_for_health():
    assert "sudo sed -i '/^GIT_COMMIT=/d' \"$ENV_FILE\"" in SETUP
    assert 'echo "GIT_COMMIT=$(sudo git -C "$APP" rev-parse HEAD)"' in SETUP
