
    const c = { template_components: "[{\"type\": \"HEADER\", \"format\": \"VIDEO\", \"example\": {\"header_handle\": [\"https://scontent.whatsapp.net/v/t61.29466-34/629183601_1312472690361383_3299587485867914122_n.mp4?ccb=1-7&_nc_sid=8b1bef&_nc_ohc=pzvKTc7Rc9QQ7kNvwH_o-_8&_nc_oc=AdqdzNnCGkmxMOj4v0vPR5_TD_VgagM7i7zCzcVtaoRCiMMCHH5RnWkPFEwgCrfvYS8&_nc_zt=28&_nc_ht=scontent.whatsapp.net&edm=AH51TzQEAAAA&_nc_gid=PvNA3IW_KI_ytsan_ZdMTQ&_nc_tpa=Q5bMBQGKr45i7du1PaBcWeSzaeXy75KGQZPt6RqAHREjaZ9HeFoIIsbN5rNJ6B7ajsDcHLzp9-UR2Utl&oh=01_Q5Aa4wH6x5byHu5ZXqXMIyFj48IK6N4-grSRZNMWqO3pO_zhSA&oe=6A50BACB\"]}}, {\"type\": \"BODY\", \"text\": \"Namaskar Ji \\ud83d\\ude4f\\u2764\\ufe0f\\nHar mahine ki shuruaat ke saath shelter aur sevaon ke kai zaroori kharch hote hain \\ud83d\\udc3e\\nIs video mein ek zaroori message hai, kripya ise zaroor dekhein \\ud83c\\udfa5\\ud83d\\ude4f\\nYadi aap Lucknow mein hain, to seva ke antargat aata, ghee, tel aur anya zaroori saamagri prapt kar sakte hain \\u2764\\ufe0f\\nDhanyawad \\ud83d\\ude4f\"}, {\"type\": \"FOOTER\", \"text\": \"Type 'stop' to turn off WhatsApp notification\"}, {\"type\": \"BUTTONS\", \"buttons\": [{\"type\": \"URL\", \"text\": \"Donate Now\", \"url\": \"https://pages.razorpay.com/pl_Sp8ih8CNrCXUlk/view\"}, {\"type\": \"QUICK_REPLY\", \"text\": \"Report a Rescue\"}]}]" };
    let buttonsHtml = '';
    let footerHtml = '';
    if (c.template_components) {
        try {
            const comps = JSON.parse(c.template_components);
            const footer = comps.find(comp => comp.type === 'FOOTER');
            if (footer && footer.text) {
                footerHtml = `<div class="text-[10px] text-slate-400 mt-1">${footer.text}</div>`;
            }
            const btns = comps.find(comp => comp.type === 'BUTTONS');
            if (btns && btns.buttons && btns.buttons.length > 0) {
                buttonsHtml = 'BUTTONS FOUND';
            }
            console.log("FOOTER:", footerHtml);
            console.log("BUTTONS:", buttonsHtml);
        } catch(e) {
            console.error(e);
        }
    }
    