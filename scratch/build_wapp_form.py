import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the wapp_form node in Drawflow
old_wapp_node = r"""            else if\(name === 'wapp_form'\) \{
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-indigo-50 text-indigo-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01\.707\.293l5\.414 5\.414a1 1 0 01\.293\.707V19a2 2 0 01-2 2z"></path></svg></div> WAPP Form</div> <svg class="w-4 h-4" onclick="editor\.removeNodeId\('node-'\+this\.parentElement\.parentElement\.id\.slice\(5\)\)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-2">
                    <input df-form_id type="text" class="w-full text-sm border border-slate-200 rounded p-2" placeholder="Form ID">
                </div>
                `;
                editor\.addNode\('wapp_form', 1, 1, pos_x, pos_y, 'wapp_form', \{ "action": "wapp_form", "form_id": "" \}, html\);
            \}"""

new_wapp_node = """            else if(name === 'wapp_form') {
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-indigo-50 text-indigo-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg></div> WAPP Form</div> <svg class="w-4 h-4" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-3 bg-[#fdfaf3]">
                    <select df-form_id class="w-full text-sm border border-slate-300 rounded p-2 bg-white outline-none">
                        <option value="">Select Formname</option>
                    </select>
                    <button onclick="openWappFormManager()" class="w-full bg-[#b8860b] hover:bg-[#a07409] text-white font-bold py-2.5 px-4 rounded shadow-sm transition-colors text-sm">Manage WAPP Form</button>
                </div>
                `;
                editor.addNode('wapp_form', 1, 1, pos_x, pos_y, 'wapp_form', { "action": "wapp_form", "form_id": "" }, html);
            }"""

content = re.sub(old_wapp_node, new_wapp_node, content)


# 2. Add Modal HTML and Logic
modal_html = """
    <!-- WAPP Form Manager Modal -->
    <div id="wappFormModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200000] hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-300">
            <!-- Header -->
            <div class="px-8 py-5 border-b border-slate-100 flex justify-between items-center bg-white shadow-sm z-10">
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2">
                        <svg class="w-6 h-6 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
                        <h3 class="text-xl font-bold text-slate-800">Create WAPP Form</h3>
                    </div>
                    <button class="bg-amber-500 hover:bg-amber-600 text-white px-4 py-1.5 rounded text-sm font-bold shadow-sm transition-colors">View Saved Form</button>
                </div>
                <button onclick="closeWappFormManager()" class="text-slate-400 hover:text-rose-500 transition-colors">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <!-- Content -->
            <div class="flex-grow overflow-y-auto p-8 bg-slate-50">
                <div class="bg-white rounded-xl shadow-sm border border-slate-100 p-6 space-y-8">
                    <!-- Form Name & Preview -->
                    <div class="flex gap-4 items-center">
                        <div class="flex flex-1 items-center gap-0">
                            <span class="bg-emerald-400 text-white px-4 py-2 rounded-l-lg text-sm font-bold whitespace-nowrap">Form Name</span>
                            <input type="text" id="wappFormName" class="flex-1 border border-slate-200 rounded-r-lg px-4 py-2 outline-none focus:ring-2 focus:ring-emerald-400 text-sm" placeholder="Enter Form Name">
                        </div>
                        <button class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-bold shadow-sm shadow-blue-500/30 transition-colors">Preview Sample Form</button>
                    </div>

                    <!-- Questions Section -->
                    <div class="space-y-4">
                        <div class="grid grid-cols-12 gap-6 text-center text-slate-500 font-bold">
                            <div class="col-span-8">Questions</div>
                            <div class="col-span-4">Question Format</div>
                        </div>

                        <div id="wappFormQuestions" class="space-y-4">
                            <!-- Single Question Row -->
                            <div class="grid grid-cols-12 gap-6 items-start bg-slate-50/50 p-4 rounded-xl border border-slate-100 question-row">
                                <div class="col-span-8">
                                    <textarea class="w-full border border-slate-200 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-emerald-400 text-sm" rows="2" placeholder="Enter question"></textarea>
                                </div>
                                <div class="col-span-4 flex items-start gap-4">
                                    <select class="flex-1 border border-slate-200 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-emerald-400 text-sm bg-white">
                                        <option value="IMAGE">IMAGE</option>
                                        <option value="TEXT">TEXT</option>
                                        <option value="NUMBER">NUMBER</option>
                                        <option value="DATE">DATE</option>
                                        <option value="LIST">LIST MENU</option>
                                    </select>
                                    <button onclick="this.closest('.question-row').remove()" class="bg-rose-500 hover:bg-rose-600 text-white px-4 py-2.5 rounded-lg text-sm font-bold shadow-sm shadow-rose-500/30 transition-colors">Delete</button>
                                </div>
                            </div>
                        </div>

                        <button onclick="addWappQuestion()" class="bg-emerald-400 hover:bg-emerald-500 text-white px-6 py-2 rounded-lg text-sm font-bold shadow-sm shadow-emerald-400/30 transition-colors mt-2">Add New Question</button>
                    </div>

                    <!-- Webhook Section -->
                    <div class="flex gap-4 items-start pt-6 border-t border-slate-100">
                        <div class="flex flex-1 items-start gap-0">
                            <span class="bg-emerald-400 text-white px-4 py-3 rounded-l-lg text-sm font-bold whitespace-nowrap mt-1">Webhook URL</span>
                            <textarea class="flex-1 border border-slate-200 rounded-r-lg px-4 py-3 outline-none focus:ring-2 focus:ring-emerald-400 text-sm mt-1" rows="2" placeholder="https://your-webhook.com/endpoint"></textarea>
                        </div>
                        <button class="bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 mt-1 rounded-lg text-sm font-bold shadow-sm shadow-amber-500/30 transition-colors whitespace-nowrap">View Webhook Format</button>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="px-8 py-5 border-t border-slate-100 bg-white flex gap-3">
                <button onclick="closeWappFormManager()" class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm shadow-blue-500/30 transition-colors">Save WhatsApp Form</button>
                <button class="bg-amber-500 hover:bg-amber-600 text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm shadow-amber-500/30 transition-colors">View Saved Forms</button>
                <button class="bg-purple-500 hover:bg-purple-600 text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm shadow-purple-500/30 transition-colors">Advanced Options</button>
            </div>
        </div>
    </div>
"""

js_code = """
        function openWappFormManager() {
            document.getElementById('wappFormModal').classList.remove('hidden');
            document.getElementById('wappFormModal').classList.add('flex');
        }

        function closeWappFormManager() {
            document.getElementById('wappFormModal').classList.add('hidden');
            document.getElementById('wappFormModal').classList.remove('flex');
            showToast("WAPP Form Saved!", "success");
        }

        function addWappQuestion() {
            const container = document.getElementById('wappFormQuestions');
            const row = document.createElement('div');
            row.className = 'grid grid-cols-12 gap-6 items-start bg-slate-50/50 p-4 rounded-xl border border-slate-100 question-row';
            row.innerHTML = `
                <div class="col-span-8">
                    <textarea class="w-full border border-slate-200 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-emerald-400 text-sm" rows="2" placeholder="Enter question"></textarea>
                </div>
                <div class="col-span-4 flex items-start gap-4">
                    <select class="flex-1 border border-slate-200 rounded-lg px-4 py-3 outline-none focus:ring-2 focus:ring-emerald-400 text-sm bg-white">
                        <option value="IMAGE">IMAGE</option>
                        <option value="TEXT">TEXT</option>
                        <option value="NUMBER">NUMBER</option>
                        <option value="DATE">DATE</option>
                        <option value="LIST">LIST MENU</option>
                    </select>
                    <button onclick="this.closest('.question-row').remove()" class="bg-rose-500 hover:bg-rose-600 text-white px-4 py-2.5 rounded-lg text-sm font-bold shadow-sm shadow-rose-500/30 transition-colors">Delete</button>
                </div>
            `;
            container.appendChild(row);
        }
"""

# Insert modal
content = content.replace("    <!-- Confirm Clear Modal -->", modal_html + "\n    <!-- Confirm Clear Modal -->")

# Insert JS before </script>
content = content.replace("</script>\n        <!-- Chatbot Builder -->", js_code + "\n</script>\n        <!-- Chatbot Builder -->")


with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
