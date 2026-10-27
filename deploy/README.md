# Deploying and operating the server

The app runs on a Linux VM as the systemd service `interactivestories` (gunicorn, see `gunicorn.config.py`).
The VM is only reachable from the campus network/VPN, so instead of GitHub pushing to it, the VM checks
GitHub every minute and deploys new commits on `main` by itself.

- **Database:** SQLite at `instance/stories.db` (not in git). Backed up automatically to Azure Blob Storage
  after every change and restored from the newest backup when the file is missing. See the main README.
- **Files (PDFs, thumbnails):** Azure Blob Storage.
- **Secrets:** `.env` in the app folder (not in git). See `.env.example`.

## Auto-deploy

`interactivestories-deploy.timer` runs `deploy/deploy.sh` every minute. The script:

1. Fetches `origin/main` and stops if it's already deployed (the last deployed commit is kept in `instance/.deployed-commit`).
2. Resets the app folder to `origin/main`. `.env`, `instance/` and `uploads/` are git-ignored, so they're kept.
3. Runs `uv sync --frozen`, restarts `interactivestories`, and checks it's running.

A failed deploy is retried every minute until it succeeds or a fix is pushed.

```bash
journalctl -u interactivestories-deploy -f                          # watch deploys
sudo systemctl start interactivestories-deploy                      # check for a new commit now
sudo -u APP_USER env FORCE=1 bash APP_DIR/deploy/deploy.sh          # redeploy the current commit
sudo systemctl disable --now interactivestories-deploy.timer        # pause auto-deploy
```

### One-time setup on the VM

Run these as an admin on the VM. Replace the two values first:

```bash
APP_USER=...   # the user the app runs as:     systemctl show -p User interactivestories
APP_DIR=...    # the app's git clone (absolute): systemctl show -p WorkingDirectory interactivestories
```

1. **Check the service runs from `APP_DIR/.venv`.** Deploys install packages with `uv` into `APP_DIR/.venv`.

   ```bash
   systemctl cat interactivestories
   ```

   `ExecStart` should be `APP_DIR/.venv/bin/gunicorn -c gunicorn.config.py wsgi:app`. If it points at
   another virtualenv, edit it (`sudo systemctl edit --full interactivestories`).

2. **Make sure `uv` is installed for `APP_USER`.**

   ```bash
   sudo -u "$APP_USER" bash -lc 'command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh'
   ```

3. **Allow `APP_USER` to restart the app, and nothing else, without a password.**

   ```bash
   echo "$APP_USER ALL=(root) NOPASSWD: $(command -v systemctl) restart interactivestories" \
     | sudo tee /etc/sudoers.d/interactivestories-deploy
   sudo chmod 440 /etc/sudoers.d/interactivestories-deploy
   sudo visudo -c
   ```

4. **Copy the database somewhere safe, then do the first deploy.** Older commits tracked `instance/stories.db`;
   the deploy script keeps your copy, but take one anyway.

   ```bash
   sudo cp "$APP_DIR/instance/stories.db" /var/tmp/stories.db.before-autodeploy
   cd "$APP_DIR"
   sudo -u "$APP_USER" git remote set-url origin https://github.com/LeanKhan/interactivestories.git
   sudo -u "$APP_USER" git fetch origin main
   sudo -u "$APP_USER" git show origin/main:deploy/deploy.sh > /tmp/deploy.sh
   sudo -u "$APP_USER" env FORCE=1 APP_DIR="$APP_DIR" bash /tmp/deploy.sh
   ```

5. **Install and start the timer.**

   ```bash
   for f in interactivestories-deploy.service interactivestories-deploy.timer; do
     sed -e "s|APP_USER|$APP_USER|g" -e "s|APP_DIR|$APP_DIR|g" "$APP_DIR/deploy/$f" \
       | sudo tee "/etc/systemd/system/$f" > /dev/null
   done
   sudo systemctl daemon-reload
   sudo systemctl enable --now interactivestories-deploy.timer
   systemctl list-timers interactivestories-deploy
   ```

6. **Make the first database backup.**

   ```bash
   cd "$APP_DIR" && sudo -u "$APP_USER" .venv/bin/flask --app app backup-db
   ```

Push a small change to `main` and run `journalctl -u interactivestories-deploy -f` to confirm it deploys within a minute.

## Moving to a new Azure storage account

The database stores blob *names* (e.g. `pdfs/story.pdf`), not full URLs, so nothing in the database
changes. Only the connection string in `.env` does.

1. **Create the new storage account** in the Azure Portal (Standard performance, LRS redundancy is enough).
   Under **Settings > Configuration**, turn on **Allow Blob anonymous access**. The site links to PDFs and
   thumbnails directly, so that container must be publicly readable. The backups container stays private.
2. **Copy its connection string** from **Security + networking > Access keys**.
3. **Stop changes on the old account.** On the VM, take a final backup and stop the app so no uploads land
   in the old account mid-move:

   ```bash
   cd "$APP_DIR" && sudo -u "$APP_USER" .venv/bin/flask --app app backup-db
   sudo systemctl stop interactivestories
   ```

4. **Copy everything across.** From the app folder (on the VM or any machine with the code and `uv`):

   ```bash
   SOURCE_AZURE_STORAGE_CONNECTION_STRING="<old connection string>" \
   DEST_AZURE_STORAGE_CONNECTION_STRING="<new connection string>" \
   uv run python scripts/migrate_storage.py
   ```

   This copies the containers named by `AZURE_CONTAINER_NAME` and `AZURE_BACKUP_CONTAINER_NAME`
   (or pass container names as arguments). It keeps each container's public/private setting and each file's
   content type. It's safe to re-run, and blobs that are already there are skipped. Every line should end
   with ✅ and matching counts.

5. **Point the app at the new account.** In `APP_DIR/.env`, set `AZURE_STORAGE_CONNECTION_STRING` to the
   new connection string, then:

   ```bash
   sudo systemctl start interactivestories
   ```

6. **Check:** stories and thumbnails load on the site (right-click a PDF link: the URL should use the new
   account name), and after an edit in `/admin`, a new file appears in the new account's backups container.
7. **Delete the old storage account** after a week or so of the new one working.
