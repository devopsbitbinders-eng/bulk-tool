import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add Drawflow CSS/JS to Head
head_pattern = r"""    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.css" />"""
new_head = """    <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/daterangepicker/daterangepicker.css" />
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/jerosoler/Drawflow/dist/drawflow.min.css">
    <script src="https://cdn.jsdelivr.net/gh/jerosoler/Drawflow/dist/drawflow.min.js"></script>
    <style>
        /* Drawflow Customizations */
        .drawflow .drawflow-node { background: white; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); padding: 0; min-width: 250px; }
        .drawflow .drawflow-node.selected { background: white; border: 2px solid #10b981; }
        .drawflow .drawflow-node .title-box { background: #f8fafc; padding: 12px 16px; border-bottom: 1px solid #e2e8f0; font-weight: bold; border-radius: 12px 12px 0 0; color: #1e293b; display: flex; justify-content: space-between; align-items: center; }
        .drawflow .drawflow-node .title-box svg { cursor: pointer; color: #ef4444; }
        .drawflow .drawflow-node .box { padding: 16px; }
        .drawflow .connection .main-path { stroke: #94a3b8; stroke-width: 3px; }
        .drawflow .connection .main-path:hover { stroke: #10b981; }
        .drawflow .drawflow-node .input, .drawflow .drawflow-node .output { width: 14px; height: 14px; background: #fff; border: 2px solid #cbd5e1; border-radius: 50%; }
        .drawflow .drawflow-node .input:hover, .drawflow .drawflow-node .output:hover { border-color: #10b981; background: #ecfdf5; }
        #drawflow { width: 100%; height: calc(100vh - 200px); background: #f8fafc; background-image: radial-gradient(#e2e8f0 1px, transparent 1px); background-size: 20px 20px; }
        .drag-node { cursor: grab; padding: 12px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: #475569; transition: all 0.2s; box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05); }
        .drag-node:hover { border-color: #10b981; color: #10b981; transform: translateY(-1px); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        .drag-node:active { cursor: grabbing; }
    </style>"""
content = re.sub(head_pattern, new_head, content)

# 2. Add Chatbot Tab Content
chat_content_pattern = r"""        <!-- Admin Panel -->
        <div id="content-admin" class="hidden">"""
new_chatbot_content = """        <!-- Chatbot Builder -->
        <div id="content-chatbot" class="hidden">
            <div class="flex gap-4">
                <!-- Node Palette (Sidebar) -->
                <div class="w-64 bg-white rounded-2xl shadow-sm border border-slate-200 p-4 h-[calc(100vh-200px)] flex flex-col">
                    <div class="mb-6">
                        <h3 class="font-bold text-slate-800 text-lg">Nodes</h3>
                        <p class="text-xs text-slate-500 mt-1">Drag and drop to canvas</p>
                    </div>
                    
                    <div class="flex-1 overflow-y-auto pr-2">
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="start">
                            <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>
                            Start Flow
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="send_message">
                            <div class="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg></div>
                            Send Message
                        </div>
                        <div class="drag-node" draggable="true" ondragstart="drag(event)" data-node="condition">
                            <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg></div>
                            Condition (If/Else)
                        </div>
                    </div>
                </div>

                <!-- Canvas Area -->
                <div class="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden relative">
                    <div class="absolute top-4 left-4 z-10">
                        <select id="chatbotSelector" onchange="loadFlow(this.value)" class="bg-white border border-slate-200 text-slate-700 text-sm rounded-lg focus:ring-green-500 focus:border-green-500 block w-48 p-2.5 shadow-sm">
                            <option value="">Create New Flow...</option>
                        </select>
                    </div>
                    <div class="absolute top-4 right-4 z-10 flex gap-2">
                        <button onclick="clearCanvas()" class="bg-white border border-slate-200 text-slate-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition shadow-sm">Clear</button>
                        <button onclick="saveFlow()" class="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-bold transition shadow-md flex items-center gap-2">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
                            Save Flow
                        </button>
                    </div>
                    <div id="drawflow" ondrop="drop(event)" ondragover="allowDrop(event)"></div>
                </div>
            </div>
        </div>

        <!-- Admin Panel -->
        <div id="content-admin" class="hidden">"""
content = re.sub(chat_content_pattern, new_chatbot_content, content)


# 3. Add Drawflow initialization script
script_pattern = r"""        function switchTab\(tab\) \{"""
new_script = """        
        // --- DRAWFLOW CHATBOT LOGIC ---
        let editor = null;
        let currentFlowId = null;

        function initDrawflow() {
            if (editor) return; // Already initialized
            
            var id = document.getElementById("drawflow");
            editor = new Drawflow(id);
            editor.reroute = true;
            editor.start();

            // Load saved flows
            fetchFlows();
        }

        async function fetchFlows() {
            try {
                const res = await fetch('/api/flows');
                const flows = await res.json();
                const sel = document.getElementById('chatbotSelector');
                sel.innerHTML = '<option value="">Create New Flow...</option>';
                flows.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f.id;
                    opt.textContent = f.name;
                    sel.appendChild(opt);
                });
            } catch(e) { console.error(e); }
        }

        async function loadFlow(id) {
            if (!id) {
                currentFlowId = null;
                editor.clearModuleSelected();
                return;
            }
            try {
                const res = await fetch(`/api/flows/${id}`);
                const flow = await res.json();
                currentFlowId = flow.id;
                if (flow.flow_json) {
                    editor.import(JSON.parse(flow.flow_json));
                } else {
                    editor.clearModuleSelected();
                }
            } catch(e) { console.error(e); }
        }

        async function saveFlow() {
            const data = editor.export();
            let name = "New Flow";
            if (!currentFlowId) {
                name = prompt("Enter flow name:", "Welcome Flow");
                if (!name) return;
            }

            try {
                const res = await fetch('/api/flows', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        id: currentFlowId,
                        name: name,
                        flow_json: JSON.stringify(data)
                    })
                });
                const result = await res.json();
                if (res.ok) {
                    alert("Flow saved successfully!");
                    currentFlowId = result.id;
                    fetchFlows();
                    setTimeout(() => { document.getElementById('chatbotSelector').value = currentFlowId; }, 500);
                } else {
                    alert("Error saving flow: " + result.error);
                }
            } catch(e) {
                alert("Error saving flow");
            }
        }

        function clearCanvas() {
            if(confirm("Clear canvas? Unsaved changes will be lost.")) {
                editor.clearModuleSelected();
                currentFlowId = null;
                document.getElementById('chatbotSelector').value = "";
            }
        }

        function drag(ev) {
            ev.dataTransfer.setData("node", ev.target.getAttribute('data-node'));
        }

        function allowDrop(ev) {
            ev.preventDefault();
        }

        function drop(ev) {
            ev.preventDefault();
            var nodeType = ev.dataTransfer.getData("node");
            addNodeToDrawFlow(nodeType, ev.clientX, ev.clientY);
        }

        function addNodeToDrawFlow(name, pos_x, pos_y) {
            if(editor.editor_mode === 'fixed') return false;
            
            pos_x = pos_x * ( editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)) - (editor.precanvas.getBoundingClientRect().x * ( editor.precanvas.clientWidth / (editor.precanvas.clientWidth * editor.zoom)));
            pos_y = pos_y * ( editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)) - (editor.precanvas.getBoundingClientRect().y * ( editor.precanvas.clientHeight / (editor.precanvas.clientHeight * editor.zoom)));

            let html = '';
            
            if(name === 'start') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-emerald-100 text-emerald-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path></svg></div> Start</div></div>
                <div class="box text-sm text-slate-500">Flow starts here</div>
                `;
                editor.addNode('start', 0, 1, pos_x, pos_y, 'start', { "action": "start" }, html);
            } 
            else if(name === 'send_message') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-blue-100 text-blue-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg></div> Send Message</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box">
                    <textarea df-text class="w-full text-sm border border-slate-200 rounded p-2 focus:ring-blue-500 focus:border-blue-500" rows="3" placeholder="Enter message text..."></textarea>
                </div>
                `;
                editor.addNode('send_message', 1, 1, pos_x, pos_y, 'send_message', { "action": "send_message", "text": "" }, html);
            }
            else if(name === 'condition') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-amber-100 text-amber-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg></div> Condition</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box">
                    <input df-condition type="text" class="w-full text-sm border border-slate-200 rounded p-2 focus:ring-amber-500 focus:border-amber-500" placeholder="e.g. 'Yes'">
                    <div class="flex justify-between mt-2 text-xs text-slate-400 font-medium px-1"><span>Match</span> <span>Else</span></div>
                </div>
                `;
                editor.addNode('condition', 1, 2, pos_x, pos_y, 'condition', { "action": "condition", "condition": "" }, html);
            }
        }
        // --- END DRAWFLOW ---

        function switchTab(tab) {"""
content = re.sub(script_pattern, new_script, content)


# 4. Initialize Drawflow on tab switch
switch_tab_pattern = r"""                } else if \(tab === 'chat'\) {
                    content\.classList\.add\('flex'\);
                    loadChatContacts\(\);"""
new_switch_tab = """                } else if (tab === 'chatbot') {
                    content.classList.add('block');
                    initDrawflow();
                } else if (tab === 'chat') {
                    content.classList.add('flex');
                    loadChatContacts();"""
content = re.sub(switch_tab_pattern, new_switch_tab, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
