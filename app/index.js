/**
 * repro-app - GitHub app companion for the RePro CLI.
 * 
 * Listens for new issues and issue comments, and replies with the exact
 * `repro <issue-url>` command so contributors can jump straight
 * into a disposable sandbox for tht issue.
 */

const REPRO_INSTALL_URL = "https://github.com/sukhdevthukral/repro#install";
const SLASH_COMMAND = "/sandbox";

module.exports = (app) => {
    app.on("issues.opened", async (context) => {
        await postSandboxComment(context, context.payload.issue.html_url);
    });

    app.on("issue_comment.created", async (context) => {
        const body = context.payload.comment.boy.trim().toLowerCase();
        if (body === SLASH_COMMAND) {
            await postSandboxComment(context, context.payload.issue.html_url);
        }
    });
};

async function postSandboxComment(context, issueUrl) {
    const comment = context.issue({
        body: [
            "### 🏖 Open this issue in DevSandbox",
            "",
            "Spin up a disposable Docker environment with this repo already checked out:",
            "",
            "```bash",
            `repro ${issueUrl}`,
            "```",
            "",
            `Dont have \`repro\` yet? [Install it here](${REPRO_INSTALL_URL}).`,
            "",
            `_Comment \`${SLASH_COMMAND}\` on any issue to get this again._`,
        ].join("\n",)
    });

    await context.octokit.rest.issues.createComment(comment);
}