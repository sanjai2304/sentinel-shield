import asyncio
import websockets
import json

async def test_live_ws():
    uri = "wss://sentinel-shield-xv2q.onrender.com/ws/dashboard"
    print(f"Connecting to live WebSocket endpoint: {uri}...")
    async with websockets.connect(uri) as ws:
        print("[SUCCESS] Connected to live WebSocket!")
        
        # 1. First message is INITIAL_STATE
        msg1 = await asyncio.wait_for(ws.recv(), timeout=10.0)
        data1 = json.loads(msg1)
        print(f"[RECV] Message Type 1: {data1.get('type')}")
        recent_events = data1.get('data', {}).get('recent_events', [])
        alerts = data1.get('data', {}).get('alerts', [])
        print(f"       Loaded {len(recent_events)} baseline events, {len(alerts)} alerts.")
        
        # 2. Wait for live simulator stream broadcast
        print("Waiting for next real-time live event broadcast from simulator...")
        msg2 = await asyncio.wait_for(ws.recv(), timeout=10.0)
        data2 = json.loads(msg2)
        print(f"[RECV] Message Type 2: {data2.get('type')}")
        if data2.get('type') == 'TELEMETRY_UPDATE':
            ev = data2.get('data', {}).get('latest_event', {})
            print(f"       Live Telemetry: User '{ev.get('user_id')}' accessed '{ev.get('resource_id')}' ({ev.get('action')}) -> Anomaly: {ev.get('is_anomaly')}")
        elif data2.get('type') == 'ANOMALY_ALERT':
            al = data2.get('data', {})
            print(f"       Live Anomaly Alert: {al.get('title')} (Severity: {al.get('severity')})")
        print("\n[VERIFIED] WebSocket connections, initial handshake, and live event streaming work over the deployed public URL!")

if __name__ == "__main__":
    asyncio.run(test_live_ws())
