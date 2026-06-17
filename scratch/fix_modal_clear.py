import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

modal_html = """
    <!-- Confirm Clear Modal -->
    <div id="clearFlowModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200000] hidden items-center justify-center p-4">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm flex flex-col overflow-hidden animate-in fade-in zoom-in duration-300">
            <div class="p-6 text-center pt-8">
                <div class="w-16 h-16 bg-rose-100 rounded-full flex items-center justify-center mx-auto mb-4 text-rose-500">
                    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                </div>
                <h3 class="text-xl font-black text-slate-800 mb-2">Clear Canvas?</h3>
                <p class="text-sm text-slate-500 font-medium">Are you sure? Any unsaved changes will be permanently lost.</p>
            </div>
            <div class="px-6 py-4 border-t border-slate-100 flex gap-3 bg-slate-50">
                <button onclick="document.getElementById('clearFlowModal').classList.add('hidden')" class="flex-1 py-3 rounded-xl font-bold text-slate-600 hover:bg-slate-200 transition-colors text-sm">Cancel</button>
                <button onclick="confirmClearCanvas()" class="flex-1 py-3 rounded-xl font-bold text-white bg-rose-500 hover:bg-rose-600 transition-colors shadow-sm text-sm">Yes, Clear</button>
            </div>
        </div>
    </div>
"""

# Replace the clearCanvas() js function
clear_canvas_js = """        function clearCanvas() {
            document.getElementById('clearFlowModal').classList.remove('hidden');
            document.getElementById('clearFlowModal').classList.add('flex');
        }

        function confirmClearCanvas() {
            editor.clearModuleSelected();
            currentFlowId = null;
            document.getElementById('chatbotSelector').value = "";
            document.getElementById('clearFlowModal').classList.add('hidden');
            document.getElementById('clearFlowModal').classList.remove('flex');
            showToast("Canvas cleared", "info");
        }"""

# 1. Insert modal HTML
content = content.replace("    <!-- Save Flow Modal -->", modal_html + "\n    <!-- Save Flow Modal -->")

# 2. Replace JS clearCanvas block using regex
old_clear_canvas_pattern = r"""        function clearCanvas\(\) \{[\s\S]*?document\.getElementById\('chatbotSelector'\)\.value = "";\s*\}\s*\}"""
content = re.sub(old_clear_canvas_pattern, clear_canvas_js, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
