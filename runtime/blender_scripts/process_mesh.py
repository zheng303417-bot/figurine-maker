import bpy, bmesh, sys, os, json, argparse, traceback
from mathutils import Vector, Matrix

parser = argparse.ArgumentParser()
for arg in ('job', 'mesh', 'output'):
    parser.add_argument('--' + arg, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = os.path.abspath(args.output)
for directory in ('stages', 'print', 'previews', 'reports'):
    os.makedirs(os.path.join(out, directory), exist_ok=True)
def path(name): return os.path.join(out, name)
def objects(): return [o for o in bpy.context.scene.objects if o.type == 'MESH']
def clear(): bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
def load(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.stl': bpy.ops.wm.stl_import(filepath=filename)
    elif ext == '.obj': bpy.ops.wm.obj_import(filepath=filename)
    elif ext in ('.glb', '.gltf'): bpy.ops.import_scene.gltf(filepath=filename)
    else: raise ValueError('Unsupported input format: ' + ext)
def bounds():
    points = [o.matrix_world @ vertex.co for o in objects() for vertex in o.data.vertices]
    if not points: raise ValueError('No mesh objects')
    return ([min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)])
def dimensions():
    lo, hi = bounds()
    return [hi[i] - lo[i] for i in range(3)]


def remove_small_components():
    """Drop small disconnected fragments after scale and base are set."""
    removed = []
    for obj in objects():
        mesh = bmesh.new()
        try:
            mesh.from_mesh(obj.data)
            unseen = set(mesh.verts)
            components = []
            while unseen:
                connected = [unseen.pop()]
                for vertex in connected:
                    for edge in vertex.link_edges:
                        other = edge.other_vert(vertex)
                        if other in unseen:
                            unseen.remove(other)
                            connected.append(other)
                components.append(connected)
            if len(components) < 2:
                continue
            largest = max(components, key=len)
            discard = []
            for component in components:
                if component is largest or len(component) > len(largest) * 0.001:
                    continue
                world = [obj.matrix_world @ vertex.co for vertex in component]
                dimensions_mm = [max(p[i] for p in world) - min(p[i] for p in world) for i in range(3)]
                if max(dimensions_mm) <= 6:
                    discard.extend(component)
                    removed.append({"vertices": len(component), "dimensions_mm": dimensions_mm})
            if discard:
                bmesh.ops.delete(mesh, geom=discard, context='VERTS')
                mesh.to_mesh(obj.data)
                obj.data.update()
        finally:
            mesh.free()
    return removed


def inspect():
    total = {'non_manifold_edges': 0, 'boundary_edges': 0, 'inconsistent_winding_edges': 0, 'degenerate_faces': 0, 'faces': 0, 'part_count': 0, 'signed_component_volumes_mm3': []}
    for obj in objects():
        bm = bmesh.new(); bm.from_mesh(obj.data); bm.transform(obj.matrix_world); bm.normal_update()
        total['non_manifold_edges'] += sum(not e.is_manifold for e in bm.edges)
        total['boundary_edges'] += sum(e.is_boundary for e in bm.edges)
        total['inconsistent_winding_edges'] += sum(e.is_manifold and not e.is_contiguous for e in bm.edges)
        total['degenerate_faces'] += sum(f.calc_area() < 1e-10 for f in bm.faces)
        total['faces'] += len(bm.faces)
        unseen = set(bm.faces)
        while unseen:
            stack = [unseen.pop()]; component = []
            while stack:
                face = stack.pop(); component.append(face)
                for edge in face.edges:
                    for neighbour in edge.link_faces:
                        if neighbour in unseen: unseen.remove(neighbour); stack.append(neighbour)
            volume = sum(v0.co.dot(v1.co.cross(v2.co)) / 6 for face in component for v0, v1, v2 in [(face.verts[0], face.verts[i], face.verts[i+1]) for i in range(1,len(face.verts)-1)])
            total['signed_component_volumes_mm3'].append(volume)
        bm.free()
    total['part_count'] = len(total['signed_component_volumes_mm3'])
    total['volume_mm3'] = sum(total['signed_component_volumes_mm3'])
    total['watertight_each_part'] = total['faces'] > 0 and total['non_manifold_edges'] == 0
    return total
def preview(filename):
    lo, hi = bounds(); center = Vector([(lo[i]+hi[i])/2 for i in range(3)]); span = max(hi[i]-lo[i] for i in range(3))
    bpy.ops.object.camera_add(location=center+Vector((span*1.8,-span*2.2,span*1.5)))
    cam = bpy.context.object; cam.rotation_euler = (center-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=span*1.7
    cam.data.clip_start = max(span / 10000, 0.00001)
    cam.data.clip_end = max(span * 20, 1000)
    scene=bpy.context.scene; scene.camera=cam; scene.render.engine='BLENDER_WORKBENCH'; scene.render.resolution_x=640; scene.render.resolution_y=640; scene.render.resolution_percentage=100; scene.render.filepath=filename
    bpy.ops.render.render(write_still=True); bpy.data.objects.remove(cam,do_unlink=True)
def save_report():
    with open(path('reports/geometry.json'),'w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2)
report = {'status':'FAIL','metrics':{},'dimensions_mm':{},'preview':[],'evidence':{},'limitations':['Thin walls, overhangs, physical printability and slicer results are UNVERIFIED.','STL coordinates represent millimetres.','Normal recalculation can change orientation of nested shells; inspect visually.']}
try:
    with open(args.job,encoding='utf-8') as f: job=json.load(f)
    clear(); load(args.mesh)
    if not objects(): raise ValueError('Input has no mesh objects')
    unit=job.get('input_unit') or ('m' if args.mesh.lower().endswith(('.glb','.gltf')) else 'mm')
    factor={'mm':1,'cm':10,'m':1000,'in':25.4}.get(unit)
    if factor is None: raise ValueError('Unsupported input unit')
    matrices = [(obj, obj.matrix_world.copy()) for obj in objects()]
    for obj, matrix in matrices:
        obj.parent = None
        if obj.data.users > 1:
            obj.data = obj.data.copy()
        obj.matrix_world = Matrix.Scale(factor,4) @ matrix
    bpy.context.view_layer.update()
    report['evidence']['before'] = inspect()
    report['evidence']['before_dimensions_mm'] = dict(zip('xyz', dimensions()))
    preview(path('previews/before.png'))
    report['preview'].append('previews/before.png')
    bpy.context.scene.unit_settings.system='METRIC'; bpy.context.scene.unit_settings.scale_length=0.001
    bpy.ops.wm.save_as_mainfile(filepath=path('stages/before.blend'))
    for obj in objects():
        bm=bmesh.new(); bm.from_mesh(obj.data); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(obj.data); bm.free(); obj.data.update()
    report['fixes_applied']=['Recalculated face normals']
    lo, hi=bounds(); height=hi[2]-lo[2]; target=float(job['target_height_mm']); base=job.get('base',{}); enabled=base.get('enabled',False); thickness=float(base.get('height_mm',3)); overlap=0.2 if enabled else 0
    desired=target-thickness+overlap if enabled and job.get('height_includes_base',True) else target
    if height<=0 or desired<=0 or (enabled and thickness<=overlap): raise ValueError('Invalid model height or base dimensions')
    scale=desired/height
    transform=Matrix.Translation(Vector((0,0,thickness-overlap if enabled else 0))) @ Matrix.Scale(scale,4) @ Matrix.Translation(Vector((0,0,-lo[2])))
    for obj in objects(): obj.matrix_world=transform @ obj.matrix_world
    bpy.context.view_layer.update()
    if enabled:
        if base.get('shape','round')!='round': raise ValueError('Only round bases supported')
        figures=objects()
        if len(figures)!=1: raise ValueError('Base union requires a single mesh object')
        lo,hi=bounds()
        radius = 0.5 * ((hi[0] - lo[0]) ** 2 + (hi[1] - lo[1]) ** 2) ** 0.5 + base.get('margin_mm', 3)
        if radius<=0: raise ValueError('Invalid base radius')
        bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=radius,depth=thickness,location=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,thickness/2)); pedestal=bpy.context.object
        obj=figures[0]; bpy.context.view_layer.objects.active=obj; mod=obj.modifiers.new('Base union','BOOLEAN'); mod.operation='UNION'; mod.solver='EXACT'; mod.object=pedestal; bpy.ops.object.modifier_apply(modifier=mod.name); bpy.data.objects.remove(pedestal,do_unlink=True); report['fixes_applied'].append('Boolean union with round base')
    if job.get('remove_small_components', False):
        removed = remove_small_components()
        report['evidence']['removed_components'] = removed
        if removed:
            report['fixes_applied'].append(f'Removed {len(removed)} small disconnected fragments')
    bpy.context.view_layer.update(); report['metrics']=inspect(); expected=dimensions(); report['dimensions_mm']=dict(zip('xyz',expected)); preview(path('previews/after.png')); report['preview'].append('previews/after.png'); bpy.ops.wm.save_as_mainfile(filepath=path('stages/after.blend'))
    metrics = report['metrics']
    if (not metrics['watertight_each_part'] or metrics['inconsistent_winding_edges']
        or metrics['degenerate_faces'] or metrics['part_count'] != 1
        or any(volume <= 1e-9 for volume in metrics['signed_component_volumes_mm3'])):
        raise ValueError('Geometry gate failed: require one closed, consistently wound, positive-volume component.')
    formats=job.get('output_formats',['stl','glb','blend']); files={}
    if 'stl' in formats:
        files['stl']=path('print/figurine.stl'); bpy.ops.wm.stl_export(filepath=files['stl'],global_scale=1.0,use_scene_unit=False)
    if 'glb' in formats:
        files['glb']=path('print/figurine.glb')
        # glTF uses metres; temporarily scale world transforms while preserving original scene.
        for obj in objects(): obj.matrix_world=Matrix.Scale(0.001,4) @ obj.matrix_world
        bpy.ops.export_scene.gltf(filepath=files['glb'],export_format='GLB')
        for obj in objects(): obj.matrix_world=Matrix.Scale(1000,4) @ obj.matrix_world
    if 'blend' in formats:
        files['blend']=path('print/figurine.blend'); bpy.ops.wm.save_as_mainfile(filepath=files['blend'])
    checks={}
    for fmt, filename in files.items():
        clear()
        if fmt=='blend': bpy.ops.wm.open_mainfile(filepath=filename)
        else:
            if fmt == 'glb':
                bpy.context.scene.unit_settings.scale_length = 1.0
            load(filename)
        bpy.context.view_layer.update(); actual=dimensions(); actual=[v*1000 for v in actual] if fmt=='glb' else actual
        checks[fmt]={'pass':os.path.getsize(filename)>0 and bool(objects()) and all(abs(a-b)<=max(0.02,abs(b)*0.0001) for a,b in zip(actual,expected)), 'dimensions_mm':dict(zip('xyz',actual))}
    report['evidence']['reopen_checks']=checks
    m=report['metrics']; single=job.get('parts',{}).get('mode','single')=='single'; height_expected=target if job.get('height_includes_base',True) or not enabled else target+thickness-overlap
    report['evidence']['height_within_tolerance']=abs(expected[2]-height_expected)<=0.5
    report['status']='PASS' if m['watertight_each_part'] and not m['degenerate_faces'] and all(v>1e-9 for v in m['signed_component_volumes_mm3']) and (not single or m['part_count']==1) and all(c['pass'] for c in checks.values()) and report['evidence']['height_within_tolerance'] else 'FAIL'
except Exception as exc:
    report['error']=str(exc); traceback.print_exc()
finally: save_report()
if report['status']!='PASS': sys.exit(1)
