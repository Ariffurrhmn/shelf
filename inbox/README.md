# Inbox

Drop an `.html` file here (from the GitHub web page: **Add file → Create new file**, name it `inbox/anything.html`, paste the HTML from your AI chat, and choose **Create a new branch and start a pull request**). A workflow turns it into an artifact on that pull request; merge it to publish.

- A file named after an existing artifact (`focus-timer.html` when `artifacts/focus-timer/` exists) **updates** that artifact. Any other name adds a new one.
- The AI's metadata block (from the "Spec + prompt" text) is used as is. If something required is missing, the pull request gets a comment saying what.
- Nothing in here is ever run. Files are read and validated, moved to `artifacts/<slug>/`, and deleted from the inbox.
- **Do not put secrets in a file here.** The repository is public, so anything committed is public even on a branch, and the scan runs after the upload. If one slips in, delete the branch and rotate the key. To scan before anything is committed, use `python shelf add --clipboard` on your computer instead.

Details: [`docs/ai-workflow.md`](../docs/ai-workflow.md).
