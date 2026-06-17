import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update palette colors
palette_replacements = [
    (r'bg-emerald-100 text-emerald-600', r'bg-emerald-50 text-emerald-600'), # start
    (r'bg-blue-100 text-blue-600', r'bg-indigo-50 text-indigo-600'), # send_message
    (r'bg-amber-100 text-amber-600', r'bg-slate-100 text-slate-600'), # condition
    
    (r'bg-blue-500 text-white', r'bg-indigo-50 text-indigo-600'), # text_reply
    (r'bg-red-500 text-white', r'bg-indigo-50 text-indigo-600'), # text_button
    (r'bg-indigo-500 text-white', r'bg-indigo-50 text-indigo-600'), # media_button
    (r'bg-green-500 text-white', r'bg-indigo-50 text-indigo-600'), # text_list
    (r'bg-cyan-500 text-white', r'bg-indigo-50 text-indigo-600'), # url_button
    (r'bg-orange-400 text-white', r'bg-indigo-50 text-indigo-600'), # media_caption
    (r'bg-blue-400 text-white', r'bg-indigo-50 text-indigo-600'), # request_location
    (r'bg-yellow-200 text-yellow-700', r'bg-indigo-50 text-indigo-600'), # wapp_form
    
    (r'bg-purple-400 text-white', r'bg-slate-100 text-slate-600'), # add_group
    (r'bg-yellow-300 text-yellow-800', r'bg-slate-100 text-slate-600'), # add_tag
    (r'bg-slate-400 text-white', r'bg-slate-100 text-slate-600'), # push_webhook
    (r'bg-emerald-400 text-white', r'bg-slate-100 text-slate-600'), # create_ticket
    (r'bg-teal-500 text-white', r'bg-slate-100 text-slate-600'), # connect_agents
    
    (r'bg-rose-600 text-white', r'bg-rose-50 text-rose-600'), # opt_out
    (r'bg-cyan-400 text-white', r'bg-emerald-50 text-emerald-600'), # connect_flow
]

for old, new in palette_replacements:
    content = re.sub(old, new, content)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
