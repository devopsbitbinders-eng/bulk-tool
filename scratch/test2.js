
    const c = {"id": 143, "name": "Imp Member - Sheet43.csv", "timestamp": "2026-06-04T15:44:40", "template_name": "monthyl_expense", "media_url": null, "t_media_url": null, "message_template": "Namaskar Ji \ud83d\ude4f\u2764\ufe0f\r\nHar mahine ki shuruaat ke saath shelter aur sevaon ke kai zaroori kharch hote hain \ud83d\udc3e\r\nIs video mein ek zaroori message hai, kripya ise zaroor dekhein \ud83c\udfa5\ud83d\ude4f\r\nYadi aap Lucknow mein hain, to seva ke antargat aata, ghee, tel aur anya zaroori saamagri prapt kar sakte hain \u2764\ufe0f\r\nDhanyawad \ud83d\ude4f", "template_components": "[{\"type\": \"HEADER\", \"format\": \"VIDEO\", \"example\": {\"header_handle\": [\"https://scontent.whatsapp.net/v/t61.29466-34/629183601_1312472690361383_3299587485867914122_n.mp4?ccb=1-7&_nc_sid=8b1bef&_nc_ohc=pzvKTc7Rc9QQ7kNvwH_o-_8&_nc_oc=AdqdzNnCGkmxMOj4v0vPR5_TD_VgagM7i7zCzcVtaoRCiMMCHH5RnWkPFEwgCrfvYS8&_nc_zt=28&_nc_ht=scontent.whatsapp.net&edm=AH51TzQEAAAA&_nc_gid=PvNA3IW_KI_ytsan_ZdMTQ&_nc_tpa=Q5bMBQGKr45i7du1PaBcWeSzaeXy75KGQZPt6RqAHREjaZ9HeFoIIsbN5rNJ6B7ajsDcHLzp9-UR2Utl&oh=01_Q5Aa4wH6x5byHu5ZXqXMIyFj48IK6N4-grSRZNMWqO3pO_zhSA&oe=6A50BACB\"]}}, {\"type\": \"BODY\", \"text\": \"Namaskar Ji \\ud83d\\ude4f\\u2764\\ufe0f\\nHar mahine ki shuruaat ke saath shelter aur sevaon ke kai zaroori kharch hote hain \\ud83d\\udc3e\\nIs video mein ek zaroori message hai, kripya ise zaroor dekhein \\ud83c\\udfa5\\ud83d\\ude4f\\nYadi aap Lucknow mein hain, to seva ke antargat aata, ghee, tel aur anya zaroori saamagri prapt kar sakte hain \\u2764\\ufe0f\\nDhanyawad \\ud83d\\ude4f\"}, {\"type\": \"FOOTER\", \"text\": \"Type 'stop' to turn off WhatsApp notification\"}, {\"type\": \"BUTTONS\", \"buttons\": [{\"type\": \"URL\", \"text\": \"Donate Now\", \"url\": \"https://pages.razorpay.com/pl_Sp8ih8CNrCXUlk/view\"}, {\"type\": \"QUICK_REPLY\", \"text\": \"Report a Rescue\"}]}]"};
    let finalMediaHtml = '';
    let headerUrl = c.media_url || c.t_media_url || "";
    let headerType = "NONE";
    let buttonsHtml = '';
    let footerHtml = '';
    
    if (c.template_components) {
        try {
            const comps = JSON.parse(c.template_components);
            const header = comps.find(comp => comp.type === 'HEADER');
            if (header) {
                headerType = header.format || "NONE";
                if (!headerUrl && header.example) {
                    headerUrl = (header.example.header_handle && header.example.header_handle[0]) || 
                                (header.example.header_text && header.example.header_text[0]) || "";
                }
            }
            const footer = comps.find(comp => comp.type === 'FOOTER');
            if (footer && footer.text) {
                footerHtml = `<div class="text-[10px] text-slate-400 mt-1">${footer.text}</div>`;
            }
            const btns = comps.find(comp => comp.type === 'BUTTONS');
            if (btns && btns.buttons && btns.buttons.length > 0) {
                buttonsHtml = '<div class="mt-2 border-t border-slate-200 pt-1 flex flex-col gap-1">BUTTONS INJECTED</div>';
            }
        } catch(e) {
            console.error("PARSE ERROR", e);
        }
    }
    
    if (headerUrl && headerType !== "NONE" && headerType !== "TEXT") {
        if (headerType === "VIDEO") {
            finalMediaHtml = `<video src="${headerUrl}" controls></video>`;
        }
    }
    
    console.log("FINAL MEDIA:", finalMediaHtml);
    console.log("FOOTER:", footerHtml);
    console.log("BUTTONS:", buttonsHtml);
    