"""Render or refine the project's synthetic robot with matched review cameras."""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def mesh_objects():
    return [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]


def render_view(output, name, position):
    scene = bpy.context.scene
    for obj in mesh_objects():
        for face in obj.data.polygons:
            face.use_smooth = (obj.matrix_world @ face.center).z > 4.05
    target = Vector((0, 0, 77))
    bpy.ops.object.camera_add(location=target + Vector(position))
    camera = bpy.context.object
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 190
    camera.data.clip_end = 2000
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.62, 0.65, 0.67)
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.render.resolution_x = 720
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.filepath = str(output / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)


def add_feature(body, name, x, z, size):
    bpy.context.view_layer.update()
    hit, location, normal, polygon = body.ray_cast(
        body.matrix_world.inverted() @ Vector((x, 300, z)), Vector((0, -1, 0))
    )
    if not hit:
        raise ValueError(f"Feature {name} does not intersect the existing mesh.")
    surface = body.matrix_world @ location
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=48, ring_count=24, location=(x, surface.y - size[1] * 0.5, z)
    )
    feature = bpy.context.object
    feature.name = name
    feature.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.objects.active = body
    modifier = body.modifiers.new(name, "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = feature
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(feature, do_unlink=True)


def refine_robot(output):
    body, = mesh_objects()
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    group = body.vertex_groups.new(name="Body excluding pedestal")
    group.add([vertex.index for vertex in body.data.vertices if vertex.co.z > 5], 1.0, "REPLACE")
    smoothing = body.modifiers.new("Reduce reconstruction stair steps", "SMOOTH")
    smoothing.vertex_group = group.name
    smoothing.factor = 0.6
    smoothing.iterations = 7
    bpy.ops.object.modifier_apply(modifier=smoothing.name)
    # Only resize the pedestal's outer rim, away from the foot intersections.
    for vertex in body.data.vertices:
        if vertex.co.z <= 4.01:
            radius = math.hypot(vertex.co.x, vertex.co.y)
            if radius > 50:
                factor = (50 + (radius - 50) * 0.45) / radius
                vertex.co.x *= factor
                vertex.co.y *= factor
    body.data.update()
    add_feature(body, "Face panel relief", -3, 117, (22, 5, 12))
    add_feature(body, "Left eye relief", -11, 118, (3.2, 3.5, 4))
    add_feature(body, "Right eye relief", 5, 118, (3.2, 3.5, 4))
    for polygon in body.data.polygons:
        polygon.use_smooth = polygon.center.z > 4.05
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "refined.blend"))
    bpy.ops.wm.stl_export(filepath=str(output / "refined.stl"), use_scene_unit=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--refine", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(args.source.resolve()))
    if args.refine:
        refine_robot(args.output)
    meshes = mesh_objects()
    points = [obj.matrix_world @ vertex.co for obj in meshes for vertex in obj.data.vertices]
    limits = {axis: [min(point[index] for point in points), max(point[index] for point in points)]
              for index, axis in enumerate("xyz")}
    (args.output / "bounds.json").write_text(json.dumps(limits, indent=2), encoding="utf-8")
    for name, direction in (
        ("negative_y", (0, -400, 0)), ("positive_y", (0, 400, 0)),
        ("negative_x", (-400, 0, 0)), ("positive_x", (400, 0, 0)),
        ("three_quarter", (240, 400, 100)),
        ("front_three_quarter", (240, -400, 100)),
    ):
        render_view(args.output, name, direction)


if __name__ == "__main__":
    main()
