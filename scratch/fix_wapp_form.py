import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update the WAPP Form node in Drawflow to match the user's first image
old_wapp_node = r"""            else if\(name === 'wapp_form'\) \{
                html = `
                <div class="title-box"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-indigo-50 text-indigo-600 flex items-center justify-center"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5\.586a1 1 0 01\.707\.293l5\.414 5\.414a1 1 0 01\.293\.707V19a2 2 0 01-2 2z"></path></svg></div> WAPP Form</div> <svg class="w-4 h-4" onclick="editor\.removeNodeId\('node-'\+this\.parentElement\.parentElement\.id\.slice\(5\)\)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-3 bg-\[\#fdfaf3\]">
                    <select df-form_id class="w-full text-sm border border-slate-300 rounded p-2 bg-white outline-none">
                        <option value="">Select Formname</option>
                    </select>
                    <button onclick="openWappFormManager\(\)" class="w-full bg-\[\#b8860b\] hover:bg-\[\#a07409\] text-white font-bold py-2\.5 px-4 rounded shadow-sm transition-colors text-sm">Manage WAPP Form</button>
                </div>
                `;
                editor\.addNode\('wapp_form', 1, 1, pos_x, pos_y, 'wapp_form', \{ "action": "wapp_form", "form_id": "" \}, html\);
            \}"""

new_wapp_node = """            else if(name === 'wapp_form') {
                html = `
                <div class="title-box" style="background: white; border-bottom: 1px solid #e2e8f0; border-radius: 12px 12px 0 0;"><div class="flex items-center gap-2"><div class="w-6 h-6 rounded bg-red-50 text-red-500 flex items-center justify-center"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg></div> <span class="text-[#1e3a8a] font-bold text-base">WAPP Form</span></div> <svg class="w-4 h-4 text-slate-400" onclick="editor.removeNodeId('node-'+this.parentElement.parentElement.id.slice(5))" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg></div>
                <div class="box space-y-3 bg-white" style="border-radius: 0 0 12px 12px;">
                    <select df-form_id class="w-full text-base border border-slate-300 rounded p-2 bg-white outline-none text-slate-800">
                        <option value="">Select Formname</option>
                    </select>
                    <button onclick="openWappFormManager()" class="w-full bg-white hover:bg-slate-50 border border-slate-100 text-transparent py-4 rounded shadow-sm transition-colors cursor-pointer"></button>
                </div>
                `;
                editor.addNode('wapp_form', 1, 1, pos_x, pos_y, 'wapp_form', { "action": "wapp_form", "form_id": "" }, html);
                
                // Add green border to the newly created node
                setTimeout(() => {
                    const nodes = document.querySelectorAll('.drawflow-node.wapp_form');
                    nodes.forEach(n => {
                        n.style.border = '2px solid #10b981';
                    });
                }, 100);
            }"""

content = re.sub(old_wapp_node, new_wapp_node, content)


# 2. Update the WAPP Form Modal HTML to match the user's second image
old_modal_pattern = r"""    <!-- WAPP Form Manager Modal -->[\s\S]*?Advanced Options</button>\s*</div>\s*</div>\s*</div>"""

new_modal_html = """    <!-- WAPP Form Manager Modal -->
    <div id="wappFormModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200000] hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-5xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in duration-300">
            <!-- Header -->
            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-white z-10">
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-2">
                        <svg class="w-6 h-6 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
                        <h3 class="text-lg font-bold text-slate-800">Create WAPP Form</h3>
                    </div>
                    <button class="bg-[#f59e0b] hover:bg-[#d97706] text-white px-3 py-1.5 rounded text-xs font-bold transition-colors">View Saved Form</button>
                </div>
                <button onclick="closeWappFormManager()" class="text-slate-400 hover:text-slate-600 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            
            <!-- Content -->
            <div class="flex-grow overflow-y-auto p-8 bg-white">
                <div class="max-w-4xl mx-auto space-y-8">
                    <!-- Form Name & Preview Row -->
                    <div class="flex gap-4 items-center">
                        <div class="flex w-2/3 items-stretch shadow-sm">
                            <span class="bg-[#10b981] text-white px-4 py-2 text-sm font-bold flex items-center justify-center whitespace-nowrap border border-[#10b981]">Form Name</span>
                            <input type="text" id="wappFormName" class="flex-1 border border-l-0 border-slate-200 px-4 py-2 outline-none text-sm placeholder-slate-400" placeholder="Enter Form Name">
                        </div>
                        <button onclick="openPreviewSampleModal()" class="bg-[#3b82f6] hover:bg-[#2563eb] text-white px-6 py-2 rounded text-sm font-bold shadow-sm transition-colors">Preview Sample Form</button>
                    </div>

                    <!-- Questions Section -->
                    <div class="space-y-4 pt-4">
                        <div class="grid grid-cols-12 gap-4 text-center text-[#475569] font-bold text-sm">
                            <div class="col-span-8">Questions</div>
                            <div class="col-span-4">Question Format</div>
                        </div>

                        <div id="wappFormQuestions" class="space-y-4">
                            <!-- Single Question Row -->
                            <div class="p-4 rounded-xl border border-slate-200 question-row shadow-sm">
                                <div class="grid grid-cols-12 gap-6 items-start">
                                    <div class="col-span-8">
                                        <textarea class="w-full border border-slate-200 rounded px-4 py-3 outline-none text-sm resize-none placeholder-slate-400" rows="2" placeholder="Enter question"></textarea>
                                    </div>
                                    <div class="col-span-4 flex items-center gap-3">
                                        <select class="flex-1 border border-slate-200 rounded px-3 py-2.5 outline-none text-sm bg-white text-slate-700">
                                            <option value="IMAGE">IMAGE</option>
                                            <option value="TEXT">TEXT</option>
                                            <option value="NUMBER">NUMBER</option>
                                            <option value="DATE">DATE</option>
                                            <option value="LIST">LIST MENU</option>
                                        </select>
                                        <button onclick="this.closest('.question-row').remove()" class="bg-[#ef4444] hover:bg-[#dc2626] text-white px-4 py-2.5 rounded text-sm font-bold shadow-sm transition-colors">Delete</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <button onclick="addWappQuestion()" class="bg-[#10b981] hover:bg-[#059669] text-white px-6 py-2 rounded text-sm font-bold shadow-sm transition-colors mt-2">Add New Question</button>
                    </div>
                </div>
            </div>

            <!-- Footer Buttons -->
            <div class="px-8 py-5 border-t border-slate-100 bg-white flex gap-3 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
                <button onclick="closeWappFormManager()" class="bg-[#3b82f6] hover:bg-[#2563eb] text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm transition-colors">Save WhatsApp Form</button>
                <button class="bg-[#f59e0b] hover:bg-[#d97706] text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm transition-colors">View Saved Forms</button>
                <button class="bg-[#a855f7] hover:bg-[#9333ea] text-white px-6 py-2.5 rounded text-sm font-bold shadow-sm transition-colors">Advanced Options</button>
            </div>
        </div>
    </div>

    <!-- Preview Sample Form Modal -->
    <div id="previewSampleModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200005] hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">
            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-[#0b141a]">
                <h3 class="text-white font-bold">Form Preview</h3>
                <button onclick="closePreviewSampleModal()" class="text-slate-400 hover:text-white transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>
            <div class="p-6 bg-[#efeae2] h-[400px] overflow-y-auto">
                <div class="bg-white rounded-lg shadow-sm p-4 text-sm text-slate-800 space-y-4">
                    <h4 class="font-bold text-lg" id="previewFormTitle">Your Form</h4>
                    <p class="text-slate-500">Please fill out the following questions:</p>
                    <div id="previewQuestionsContainer" class="space-y-4 pt-2">
                        <!-- Filled by JS -->
                    </div>
                    <button class="w-full bg-[#00a884] text-white rounded-full py-2 font-bold mt-4">Submit</button>
                </div>
            </div>
        </div>
    </div>
"""

content = re.sub(old_modal_pattern, new_modal_html, content)

# 3. Add JS for Preview Modal
old_js_pattern = r"""        function addWappQuestion\(\) \{[\s\S]*?container\.appendChild\(row\);\s*\}"""

new_js = """        function addWappQuestion() {
            const container = document.getElementById('wappFormQuestions');
            const row = document.createElement('div');
            row.className = 'p-4 rounded-xl border border-slate-200 question-row shadow-sm';
            row.innerHTML = `
                <div class="grid grid-cols-12 gap-6 items-start">
                    <div class="col-span-8">
                        <textarea class="w-full border border-slate-200 rounded px-4 py-3 outline-none text-sm resize-none placeholder-slate-400" rows="2" placeholder="Enter question"></textarea>
                    </div>
                    <div class="col-span-4 flex items-center gap-3">
                        <select class="flex-1 border border-slate-200 rounded px-3 py-2.5 outline-none text-sm bg-white text-slate-700">
                            <option value="IMAGE">IMAGE</option>
                            <option value="TEXT">TEXT</option>
                            <option value="NUMBER">NUMBER</option>
                            <option value="DATE">DATE</option>
                            <option value="LIST">LIST MENU</option>
                        </select>
                        <button onclick="this.closest('.question-row').remove()" class="bg-[#ef4444] hover:bg-[#dc2626] text-white px-4 py-2.5 rounded text-sm font-bold shadow-sm transition-colors">Delete</button>
                    </div>
                </div>
            `;
            container.appendChild(row);
        }

        function openPreviewSampleModal() {
            const title = document.getElementById('wappFormName').value || 'Sample Form';
            document.getElementById('previewFormTitle').innerText = title;
            
            const questions = document.querySelectorAll('.question-row textarea');
            const types = document.querySelectorAll('.question-row select');
            const container = document.getElementById('previewQuestionsContainer');
            container.innerHTML = '';
            
            if(questions.length === 0) {
                container.innerHTML = '<p class="text-slate-400 italic">No questions added yet.</p>';
            } else {
                questions.forEach((q, i) => {
                    const qText = q.value || `Question ${i+1}`;
                    const qType = types[i].value;
                    let inputHtml = '';
                    if(qType === 'TEXT') inputHtml = '<input type="text" class="w-full border-b border-slate-300 outline-none py-1" placeholder="Type answer...">';
                    else if(qType === 'NUMBER') inputHtml = '<input type="number" class="w-full border-b border-slate-300 outline-none py-1" placeholder="123...">';
                    else if(qType === 'DATE') inputHtml = '<input type="date" class="w-full border-b border-slate-300 outline-none py-1">';
                    else if(qType === 'IMAGE') inputHtml = '<div class="border-2 border-dashed border-slate-300 rounded p-4 text-center text-slate-400 text-xs">Tap to upload image</div>';
                    else if(qType === 'LIST') inputHtml = '<select class="w-full border border-slate-300 rounded p-1"><option>Select option...</option></select>';
                    
                    container.innerHTML += `
                        <div class="space-y-1">
                            <p class="font-bold text-slate-700">${qText}</p>
                            ${inputHtml}
                        </div>
                    `;
                });
            }

            document.getElementById('previewSampleModal').classList.remove('hidden');
            document.getElementById('previewSampleModal').classList.add('flex');
        }

        function closePreviewSampleModal() {
            document.getElementById('previewSampleModal').classList.add('hidden');
            document.getElementById('previewSampleModal').classList.remove('flex');
        }"""

content = re.sub(old_js_pattern, new_js, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
