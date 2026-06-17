import sys

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update showCustomConfirm
content = content.replace(
    "function showCustomConfirm(title, message, onConfirmCallback) {",
    "function showCustomConfirm(title, message, onConfirmCallback, onCancelCallback = null) {"
)

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

# 2. Add ID to Confirm modal cancel button
old_html_btn = """<button onclick="closeConfirmModal()" class="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors text-sm">Cancel</button>"""
new_html_btn = """<button id="confirmModalCancelBtn" onclick="closeConfirmModal()" class="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 bg-slate-100 rounded-lg transition-colors text-sm">Cancel</button>"""
content = content.replace(old_html_btn, new_html_btn)

# 3. Add checkbox
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


# Add handleExcludeOptOutsToggle
toggle_js = """
            function handleExcludeOptOutsToggle(checkbox) {
                if (!checkbox.checked) {
                    checkbox.checked = true;
                    showCustomConfirm(
                        'Send to Opt-Outs?', 
                        'Are you absolutely sure you want to send this campaign to people who have previously opted out? This is generally not recommended.', 
                        () => { checkbox.checked = false; }
                    );
                }
            }
"""
content = content.replace("            campaignForm.onsubmit = async (e) => {", toggle_js + "\n            campaignForm.onsubmit = async (e) => {")

# Modify campaignForm.onsubmit to wrap in processSubmit
submit_start = "            campaignForm.onsubmit = async (e) => {\n                e.preventDefault();"
submit_wrapper_start = """            campaignForm.onsubmit = async (e) => {
                e.preventDefault();
                const processSubmit = async () => {
                    // Append allow_opt_outs flag
                    if (!document.getElementById('excludeOptOuts').checked) {
                        formData.append('allow_opt_outs', 'true');
                    }"""
content = content.replace(submit_start, submit_wrapper_start)

# Add formData logic inside submit block
old_formdata = "                const formData = new FormData(campaignForm);"
new_formdata = """                const formData = new FormData(campaignForm);"""
# Actually, the allow_opt_outs append happens after formData is created, so let's place it right before fetch.

# Replace processSubmit end logic
old_catch = """                    } else {
                        showToast(result.error || 'Failed to start campaign', 'error');
                        submitBtn.disabled = false;
                        submitBtn.innerText = 'Launch Campaign';
                    }
                } catch (err) {
                    console.error(err);
                    showToast('Network error, try again.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Launch Campaign';
                }
            };"""

new_catch = """                    } else {
                        showToast(result.error || 'Failed to start campaign', 'error');
                        submitBtn.disabled = false;
                        submitBtn.innerText = 'Launch Campaign';
                    }
                } catch (err) {
                    console.error(err);
                    showToast('Network error, try again.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Launch Campaign';
                }
                }; // end processSubmit
                
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
            };"""
content = content.replace(old_catch, new_catch)

# Fix formData append (since I put it at the very top of processSubmit where formData is not defined yet!)
content = content.replace("""                const processSubmit = async () => {
                    // Append allow_opt_outs flag
                    if (!document.getElementById('excludeOptOuts').checked) {
                        formData.append('allow_opt_outs', 'true');
                    }""", "                const processSubmit = async () => {")

content = content.replace(
    "const response = await fetch('/upload'",
    """// Append allow_opt_outs flag
                    if (!document.getElementById('excludeOptOuts').checked) {
                        formData.append('allow_opt_outs', 'true');
                    }
                    const response = await fetch('/upload'"""
)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
