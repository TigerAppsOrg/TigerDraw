# TigerDraw

The read-only PI connector runs as an independent companion service. See
[MCP setup and tools](mcp/README.md).

# Local Development
Install dependencies:
- `python -m venv venv`
- `./venv/bin/activate` for Mac and `venv\Scripts\activate` for Windows
- `pip install -r requirements.txt`

Env Variables: fill in .env.template and rename to .env, then uncomment lines 2-4 in config.py, run `pip install python-dotenv`, and run `python app.py`. Remember to change this back when deploying to a staging instance/prod. (or could just set the vars directly and not have to do this whole process)
