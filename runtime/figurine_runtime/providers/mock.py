import json, math, struct
from pathlib import Path

def geometry():
    # A single closed surface of revolution, in glTF Y-up coordinates.
    rings=[(0,.20),(.08,.24),(.35,.20),(.60,.27),(.85,.25),(1.0,.16),(1.08,.29),(1.30,.34),(1.52,.28),(1.62,.12)]
    n=24; vertices=[(0,0,0)]
    for y,r in rings:
        vertices.extend((r*math.cos(2*math.pi*i/n),y,r*math.sin(2*math.pi*i/n)) for i in range(n))
    vertices.append((0,1.65,0)); indices=[]
    for i in range(n): indices.extend((0,1+i,1+(i+1)%n))
    for j in range(len(rings)-1):
        a=1+j*n; b=a+n
        for i in range(n):
            k=(i+1)%n; indices.extend((a+i,b+i,a+k,a+k,b+i,b+k))
    top=len(vertices)-1; a=1+(len(rings)-1)*n
    for i in range(n): indices.extend((a+i,top,a+(i+1)%n))
    return vertices, indices


def make_stl(vertices, indices):
    # Rotate Y-up to Z-up, convert metres to millimetres, preserve winding.
    millimetres = [(x * 1000, -z * 1000, y * 1000) for x, y, z in vertices]
    triangles = bytearray(b"Figurine Maker synthetic mock".ljust(80, b"\0"))
    triangles.extend(struct.pack("<I", len(indices) // 3))
    for offset in range(0, len(indices), 3):
        points = [millimetres[index] for index in indices[offset:offset + 3]]
        triangles.extend(struct.pack("<12fH", 0, 0, 0, *points[0], *points[1], *points[2], 0))
    return triangles


def make_glb(vertices, indices):
    vb=b''.join(struct.pack('<3f',*v) for v in vertices); ib=struct.pack('<%dH'%len(indices),*indices); binary=vb+ib
    doc={'asset':{'version':'2.0','generator':'figurine-maker mock'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1}]}],'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(vb),'target':34962},{'buffer':0,'byteOffset':len(vb),'byteLength':len(ib),'target':34963}],'accessors':[{'bufferView':0,'componentType':5126,'count':len(vertices),'type':'VEC3','min':[min(v[i] for v in vertices) for i in range(3)],'max':[max(v[i] for v in vertices) for i in range(3)]},{'bufferView':1,'componentType':5123,'count':len(indices),'type':'SCALAR'}]}
    js=json.dumps(doc,separators=(',',':')).encode(); js+=b' '*((-len(js))%4); binary+=b'\0'*((-len(binary))%4)
    return struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(binary))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary


def generate(destination):
    path = Path(destination)
    vertices, indices = geometry()
    if path.suffix == ".stl":
        data = make_stl(vertices, indices)
    elif path.suffix == ".glb":
        data = make_glb(vertices, indices)
    else:
        raise ValueError("Mock output must be STL or GLB.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {"provider": "mock", "task_id": None, "status": "SUCCEEDED", "synthetic": True}
