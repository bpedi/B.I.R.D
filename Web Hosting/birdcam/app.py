from flask import Flask, render_template, request, jsonify
from aiortc import RTCPeerConnection, RTCSessionDescription
import asyncio
import json
import uuid
import aiohttp
import ssl

app = Flask(__name__, template_folder='templates')
pcs = {}  # Store peer connections by ID
ice_candidates = {}  # Store ICE candidates for each peer connection

# Helper to run async tasks in Flask
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(coro)
    loop.close()
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

@app.route('/offer', methods=['POST'])
def offer():
    async def handle_offer():
        async with aiohttp.ClientSession() as session:
            params = request.json
            offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
            pc_id = f"PeerConnection({uuid.uuid4()})"
            pc = RTCPeerConnection()
            pcs[pc_id] = pc
            ice_candidates[pc_id] = []

            @pc.on("icecandidate")
            def on_icecandidate(candidate):
                if candidate:
                    ice_candidates[pc_id].append(candidate)
                    print(f"Stored ICE candidate for {pc_id}")

            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            return {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "pc_id": pc_id
            }

    return jsonify(run_async(handle_offer()))

@app.route('/add_ice_candidate', methods=['POST'])
def add_ice_candidate():
    async def handle_ice_candidate():
        params = request.json
        pc_id = params['pc_id']
        candidate = params['candidate']
        if pc_id in pcs:
            pc = pcs[pc_id]
            await pc.addIceCandidate(candidate)
            return {"status": "ICE candidate added"}
        return {"status": "error", "message": "PeerConnection not found"}

    return jsonify(run_async(handle_ice_candidate()))

@app.route('/get_ice_candidates/<pc_id>', methods=['GET'])
def get_ice_candidates(pc_id):
    return jsonify(ice_candidates.get(pc_id, []))

@app.route('/close/<pc_id>', methods=['POST'])
def close(pc_id):
    async def handle_close():
        if pc_id in pcs:
            pc = pcs[pc_id]
            await pc.close()
            del pcs[pc_id]
            del ice_candidates[pc_id]
            return {"status": "closed"}
        return {"status": "error", "message": "PeerConnection not found"}

    return jsonify(run_async(handle_close()))

if __name__ == '__main__':
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')
    app.run(host='0.0.0.0', port=5001, debug=True, ssl_context=context)