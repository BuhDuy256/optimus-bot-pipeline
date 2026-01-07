# GitHub Actions Workflows

## Daily Article Sync

The `daily-sync.yml` workflow automatically syncs articles from the API to the OpenAI Vector Store.

### Schedule

- Runs daily at 2:00 AM UTC
- Can be triggered manually from the Actions tab

### How It Works

1. **Download Previous Data**: Retrieves the `data/` folder from the last run (contains hashes and sync state)
2. **Build Docker Image**: Creates the container with the latest code
3. **Run Sync**: Executes the pipeline with delta detection
4. **Upload Data**: Saves the updated `data/` folder for the next run

### Setup Required

Add the following secret to your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add:
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

### Artifact Storage

- The `data/` folder is stored as a GitHub Actions artifact
- Retention: 90 days (automatically cleaned up after)
- This preserves delta detection state between runs

### Manual Trigger

To run manually:

1. Go to **Actions** tab
2. Select **Daily Article Sync**
3. Click **Run workflow**
