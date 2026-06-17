
# --- CHATBOT FLOW ENDPOINTS ---

@app.get("/api/flows")
async def get_flows(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    flows = await db.fetch_all("SELECT id, name, status FROM flows WHERE user_id = :u ORDER BY created_at DESC", {"u": u_id})
    return [dict(f) for f in flows]

@app.get("/api/flows/{flow_id}")
async def get_flow_by_id(flow_id: int, request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    db = await get_db()
    flow = await db.fetch_one("SELECT * FROM flows WHERE id = :id AND user_id = :u", {"id": flow_id, "u": u_id})
    if not flow: return JSONResponse(status_code=404, content={"error": "Flow not found"})
    return dict(flow)

@app.post("/api/flows")
async def save_flow(request: Request):
    session_token = request.cookies.get("session_token")
    username = verify_session_token(session_token)
    if not username: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    u_id = await get_user_id(username)
    
    data = await request.json()
    flow_id = data.get("id")
    name = data.get("name", "New Flow")
    flow_json = data.get("flow_json")
    
    db = await get_db()
    
    if flow_id:
        await db.execute("""
            UPDATE flows SET name = :n, flow_json = :j, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND user_id = :u
        """, {"n": name, "j": flow_json, "id": flow_id, "u": u_id})
    else:
        await db.execute("""
            INSERT INTO flows (user_id, name, flow_json) VALUES (:u, :n, :j)
        """, {"u": u_id, "n": name, "j": flow_json})
        # get last insert id
        res = await db.fetch_one("SELECT last_insert_rowid() as id")
        # For mysql
        if not res:
            res = await db.fetch_one("SELECT LAST_INSERT_ID() as id")
        flow_id = res['id'] if res else None
        
    return {"status": "ok", "id": flow_id}
