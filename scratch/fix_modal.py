import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

modal_html = """
    <!-- Save Flow Modal -->
    <div id="saveFlowModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200000] hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">
            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-white">
                <h3 class="text-lg font-bold text-slate-800">Save Flow</h3>
                <button onclick="document.getElementById('saveFlowModal').classList.add('hidden')" class="text-slate-400 hover:text-slate-600">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="p-6">
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Flow Name</label>
                <input type="text" id="flowNameInput" class="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-emerald-500 outline-none text-sm font-medium" placeholder="e.g. Welcome Flow">
            </div>
            <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 bg-slate-50">
                <button onclick="document.getElementById('saveFlowModal').classList.add('hidden')" class="px-5 py-2.5 rounded-xl font-bold text-slate-600 hover:bg-slate-200 transition-colors text-sm">Cancel</button>
                <button onclick="confirmSaveFlow()" class="px-5 py-2.5 rounded-xl font-bold text-white bg-emerald-500 hover:bg-emerald-600 transition-colors shadow-sm text-sm">Save Flow</button>
            </div>
        </div>
    </div>
"""

# Replace the saveFlow() js function to use the modal instead of prompt.
save_flow_js = """        async function saveFlow() {
            const data = editor.export();
            let name = "New Flow";
            if (!currentFlowId) {
                document.getElementById('flowNameInput').value = "Welcome Flow";
                document.getElementById('saveFlowModal').classList.remove('hidden');
                document.getElementById('saveFlowModal').classList.add('flex');
                return; // wait for modal confirm
            }
            // If already has an ID, just save it directly
            await executeSaveFlow(currentFlowId, null, data);
        }

        async function confirmSaveFlow() {
            const name = document.getElementById('flowNameInput').value;
            if (!name) return;
            document.getElementById('saveFlowModal').classList.add('hidden');
            document.getElementById('saveFlowModal').classList.remove('flex');
            
            const data = editor.export();
            await executeSaveFlow(null, name, data);
        }

        async function executeSaveFlow(id, name, data) {
            try {
                const res = await fetch('/api/flows', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        id: id,
                        name: name,
                        flow_json: JSON.stringify(data)
                    })
                });
                const result = await res.json();
                if (res.ok) {
                    showToast("Flow saved successfully!", "success");
                    currentFlowId = result.id;
                    fetchFlows();
                    setTimeout(() => { document.getElementById('chatbotSelector').value = currentFlowId; }, 500);
                } else {
                    showToast("Error saving flow: " + result.error, "error");
                }
            } catch(e) {
                showToast("Error saving flow", "error");
            }
        }"""

# 1. Insert modal HTML
content = content.replace("    <!-- Manual Auth Modal -->", modal_html + "\n    <!-- Manual Auth Modal -->")

# 2. Replace JS saveFlow block using regex
old_save_flow_pattern = r"""        async function saveFlow\(\) \{[\s\S]*?catch\(e\) \{\s*alert\("Error saving flow"\);\s*\}\s*\}"""
content = re.sub(old_save_flow_pattern, save_flow_js, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
