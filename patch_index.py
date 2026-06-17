import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update showCustomConfirm
old_confirm = "function showCustomConfirm(title, message, onConfirmCallback) {"
new_confirm = "function showCustomConfirm(title, message, onConfirmCallback, onCancelCallback = null) {"
content = content.replace(old_confirm, new_confirm)

old_btn = """                btn.onclick = () => {
                    closeConfirmModal();
                    onConfirmCallback();
                };"""
new_btn = """                btn.onclick = () => {
                    closeConfirmModal();
                    onConfirmCallback();
                };

                const cancelBtn = document.getElementById('confirmModalCancelBtn');
                if (cancelBtn) {
                    cancelBtn.onclick = () => {
                        closeConfirmModal();
                        if (onCancelCallback) onCancelCallback();
                    };
                }"""
content = content.replace(old_btn, new_btn)

old_html_btn = """<button onclick="closeConfirmModal()" class="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors text-sm">Cancel</button>"""
new_html_btn = """<button id="confirmModalCancelBtn" onclick="closeConfirmModal()" class="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors text-sm">Cancel</button>"""
content = content.replace(old_html_btn, new_html_btn)

old_schedule_div = """                            <div class="mb-6 p-4 bg-slate-50 rounded-2xl border border-slate-200">
                                <div class="flex items-center justify-between mb-3">
                                    <label class="flex items-center gap-2 cursor-pointer group">
                                        <input type="checkbox" id="isScheduled" name="is_scheduled"
                                            onchange="toggleScheduleInput(this.checked)"
                                            class="w-4 h-4 text-green-600 rounded border-slate-300 focus:ring-green-500">
                                        <span
                                            class="text-sm font-bold text-slate-700 group-hover:text-slate-900 transition-colors">Schedule
                                            for later</span>
                                    </label>
                                    <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor"
                                        viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                </div>
                                <div id="scheduleInputContainer" class="hidden">
                                    <label
                                        class="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Select
                                        Date & Time</label>
                                    <input type="datetime-local" id="scheduleDate" name="scheduled_at"
                                        class="w-full px-4 py-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-green-500 text-sm">
                                </div>
                            </div>"""

new_schedule_div = """                            <div class="mb-6 p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-4">
                                <div class="flex items-center justify-between">
                                    <label class="flex items-center gap-2 cursor-pointer group">
                                        <input type="checkbox" id="isScheduled" name="is_scheduled"
                                            onchange="toggleScheduleInput(this.checked)"
                                            class="w-4 h-4 text-green-600 rounded border-slate-300 focus:ring-green-500">
                                        <span class="text-sm font-bold text-slate-700 group-hover:text-slate-900 transition-colors">Schedule for later</span>
                                    </label>
                                    <svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                </div>
                                <div id="scheduleInputContainer" class="hidden border-t border-slate-200 pt-4">
                                    <label class="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wider">Select Date & Time</label>
                                    <input type="datetime-local" id="scheduleDate" name="scheduled_at" class="w-full px-4 py-2.5 rounded-xl border border-slate-200 outline-none focus:ring-2 focus:ring-green-500 text-sm">
                                </div>
                                <div class="flex items-center justify-between border-t border-slate-200 pt-4">
                                    <label class="flex items-center gap-2 cursor-pointer group">
                                        <input type="checkbox" id="excludeOptOuts" name="exclude_opt_outs" checked value="true"
                                            onchange="handleExcludeOptOutsToggle(this)"
                                            class="w-4 h-4 text-rose-600 rounded border-slate-300 focus:ring-rose-500">
                                        <span class="text-sm font-bold text-slate-700 group-hover:text-slate-900 transition-colors">Exclude Opt-Out Numbers</span>
                                    </label>
                                    <span class="text-[10px] bg-slate-200 px-2 py-0.5 rounded text-slate-600 font-bold">Recommended</span>
                                </div>
                            </div>"""
content = content.replace(old_schedule_div, new_schedule_div)


handler_js = """
            function handleExcludeOptOutsToggle(checkbox) {
                if (!checkbox.checked) {
                    checkbox.checked = true; // Revert instantly
                    showCustomConfirm(
                        'Send to Opt-Outs?', 
                        'Are you absolutely sure you want to send this campaign to people who have previously opted out? This is generally not recommended.', 
                        () => { checkbox.checked = false; } // Proceed with unchecking
                    );
                }
            }

            campaignForm.onsubmit = async (e) => {
"""
content = content.replace("            campaignForm.onsubmit = async (e) => {", handler_js)

start_idx = content.find("campaignForm.onsubmit = async (e) => {")
end_idx = content.find("        function toggleTemplateFields(show) {", start_idx)

old_submit_block = content[start_idx:end_idx]

modified_block = old_submit_block.replace(
    "const submitBtn = document.getElementById('launchBtn');",
    "// Append allow_opt_outs flag\n                if (!document.getElementById('excludeOptOuts').checked) {\n                    formData.append('allow_opt_outs', 'true');\n                }\n\n                const submitBtn = document.getElementById('launchBtn');"
)

lines = modified_block.split("\\n")
wrapped_lines = []
found_prevent = False

for line in lines:
    if "e.preventDefault();" in line and not found_prevent:
        wrapped_lines.append(line)
        wrapped_lines.append("                const processSubmit = async () => {")
        found_prevent = True
    elif "            };" in line and found_prevent:
        wrapped_lines.append("                };")
        wrapped_lines.append("""
                const checkbox = document.getElementById('excludeOptOuts');
                if (!checkbox.checked) {
                    showCustomConfirm(
                        'Final Confirmation', 
                        'You are about to launch this campaign to ALL numbers, INCLUDING those who have opted out. Are you sure you want to proceed?', 
                        () => { processSubmit(); }, 
                        () => { 
                            checkbox.checked = true;
                            processSubmit();
                        }
                    );
                } else {
                    processSubmit();
                }
            };""")
        found_prevent = False
    else:
        wrapped_lines.append(line)

content = content.replace(old_submit_block, "\\n".join(wrapped_lines))

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
