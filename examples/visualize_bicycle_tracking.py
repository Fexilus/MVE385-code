"""Visualize created tracks."""
from math import pi

import numpy as np
import open3d as o3d
import h5py

from tracking.data.load import load_point_clouds, load_detections
from tracking.visualize.pointcloud import init_point_cloud, update_point_cloud
from tracking.visualize.detections import init_detections, update_detections
from tracking.visualize.tracks import init_tracks, update_tracks
from tracking.association.association_tracking import track_multiple_objects
from tracking.filter.bicycle import predict, update, defaultStateVector, normalized_innovation, state_to_position, detection_to_position


DATA_FILE = "data/data_109.h5"
MIN_SEC = 5
DEFAULT_ANGLE = -pi / 2

# Initiate data
bounding_box = o3d.geometry.AxisAlignedBoundingBox(np.asarray((-50, -50, -50)),
                                                   np.asarray(( 50,  50,  10)))

pcloud_sequence = load_point_clouds(DATA_FILE, min_security=MIN_SEC)

det_sequence = load_detections(DATA_FILE)

# Initiate tracking

def specificDefaultStateVector(state):
    return defaultStateVector(state, DEFAULT_ANGLE)


camera = h5py.File(DATA_FILE, 'r')


def camera_detections():
    for frame in range(len(camera["Sequence"])):
        detections = camera["Sequence"][str(frame)]["Detections"]
        positions = [list(pos) for pos in detections["Pos"]]
        lengths = [max(l, w) for l, w
                    in zip(detections["Length"], detections["Width"])]

        yield [pos + [leng] for pos, leng in zip(positions, lengths)]


timestamps = iter(np.asarray(camera["Timestamp"]))

tracks_sequence = track_multiple_objects(camera_detections(), timestamps,
                                         predict, update,
                                         normalized_innovation,
                                         specificDefaultStateVector,
                                         state_to_position,
                                         detection_to_position)

# Initiate visualization
visualizer = o3d.visualization.VisualizerWithKeyCallback()
visualizer.create_window(width=800, height=600)

pcloud_geometry = init_point_cloud(visualizer, pcloud_sequence, bounding_box)

det_geometry = init_detections(visualizer, det_sequence)

tracks_geometry = init_tracks(visualizer, tracks_sequence)

# Set default camera view

def normalize(vector):
    """Normalize a vector, i.e. make the norm 1 while preserving direction."""
    return vector / np.linalg.norm(vector)


front       = np.asarray((3.0, 4.0, -1.0))
lookat      = normalize(np.asarray((0.1, 0.0, 0.0)))
world_up    = np.asarray((0.0, 0.0, -1.0))
camera_side = normalize(np.cross(front, world_up))
camera_up   = np.cross(camera_side, front)
zoom        = 0.25

view_control = visualizer.get_view_control()
view_control.set_front(front)
view_control.set_lookat(lookat)
view_control.set_up(camera_up)
view_control.set_zoom(zoom)
view_control.translate(150, 0)

# Set default render options
render_options = visualizer.get_render_option()
render_options.line_width = 15.0
render_options.point_size = 2.0


def next_frame(visualizer):
    """Callback function to progress in frame sequence."""
    global pcloud_geometry
    pcloud_geometry = update_point_cloud(visualizer, pcloud_geometry,
                                         pcloud_sequence, bounding_box)

    global det_geometry
    det_geometry = update_detections(visualizer, det_geometry, det_sequence)

    global tracks_geometry
    tracks_geometry = update_tracks(visualizer, tracks_geometry,
                                    tracks_sequence)

    # Indicate that the geometry needs updating
    return True


visualizer.register_key_callback(32, next_frame)

visualizer.run()