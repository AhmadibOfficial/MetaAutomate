# MetaAutomate Web Workspace

This is a working, responsive HTML/CSS/JavaScript frontend served on the same origin by the FastAPI application. It is **not a Next.js application**.

The workspace includes a local development sign-in, objective form, draft capability catalog, saved objectives, a visual dependency graph and review decisions. It does not provide external task execution.

Start the isolated contributor demo from repository root with:

    make demo-up

Visit http://127.0.0.1:18000/. The demo sign-in key is saved privately under examples/oss-demo/.workspace-access-key. Do not commit or share it.

The official blue/silver/gold MetaAutomate brand application and cloud SSO infrastructure are proposed separately in draft PR #6. Do not assume those features are present on main.
