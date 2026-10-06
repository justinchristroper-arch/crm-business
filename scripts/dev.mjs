import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
const python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
if(!existsSync(python))throw Error('Create .venv and install requirements-dev.txt first. See README.');
const child=spawn(python,['-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000'],{stdio:'inherit'});
child.on('exit',code=>process.exit(code||0));
