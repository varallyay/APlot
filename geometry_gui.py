#!/usr/bin/env python3
"""
Interactive 4-View 3D Geometry Builder for Ansys Lumerical (.lsf)
=================================================================
Opens a window divided into four quadrants:
  - Top-Left     : Top view (x-y)
  - Bottom-Left  : Side view / Cross section (x-z)
  - Top-Right    : 3D view (x-y-z, interactive rotation & zoom)
  - Bottom-Right : Front view / Cross section (y-z)

Features:
  - Draw connected polygon points with the mouse pointer in each 2D view
    (Top x-y, Side x-z, Front y-z).
  - Modify points at any time after drawing:
      * Drag any vertex with the left mouse button to move it.
      * Click and drag on any polygon edge midpoint (or Shift+click an edge)
        to insert a new vertex between connected points.
      * Right-click (or Ctrl+click / Delete key) on a vertex to remove it.
      * Edit exact numeric coordinates of the selected vertex in the toolbar.
  - "Generate geometry" button: Reconstructs the 3D solid from the three
    orthographic views and displays it in the 3D view.
  - "Generate file" button: Exports an Ansys Lumerical script (.lsf) matching
    the drawn and reconstructed 3D geometry.
"""

import math
import os

os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class OrthoCanvas2D(tk.Frame):
    """Interactive 2D orthographic view canvas for drawing and editing connected points."""

    def __init__(
        self,
        parent,
        title,
        u_label,
        v_label,
        u_range,
        v_range,
        u_guides=None,
        v_guides=None,
        u_grid_step=50.0,
        v_grid_step=0.25,
        on_point_selected=None,
        on_geometry_changed=None,
    ):
        super().__init__(parent, bd=1, relief=tk.SOLID, bg="#f8f9fa")
        self.title = title
        self.u_label = u_label
        self.v_label = v_label
        self.default_u_range = list(u_range)
        self.default_v_range = list(v_range)
        self.u_range = list(u_range)
        self.v_range = list(v_range)
        self.u_guides = u_guides or []
        self.v_guides = v_guides or []
        self.u_grid_step = u_grid_step
        self.v_grid_step = v_grid_step
        self.on_point_selected = on_point_selected
        self.on_geometry_changed = on_geometry_changed

        # Polygon state: list of [u, v] in physical units (micrometers)
        self.points = []
        self.closed = False
        self.selected_idx = None
        self.dragging_idx = None
        self.hover_idx = None
        self.hover_edge_idx = None
        self.cursor_uv = None
        self.snap_enabled = True

        # Panning state (middle-drag or Space+drag)
        self._pan_start = None

        # Header bar inside view
        header = tk.Frame(self, bg="#e9ecef", height=26)
        header.pack(fill=tk.X, side=tk.TOP)

        self.title_lbl = tk.Label(
            header,
            text=f"  {self.title}",
            font=("Helvetica", 11, "bold"),
            bg="#e9ecef",
            fg="#212529",
            anchor="w",
        )
        self.title_lbl.pack(side=tk.LEFT, padx=4, pady=2)

        self.coord_lbl = tk.Label(
            header,
            text="",
            font=("Courier", 10),
            bg="#e9ecef",
            fg="#495057",
        )
        self.coord_lbl.pack(side=tk.LEFT, padx=10)

        btn_clear = tk.Button(
            header,
            text="Clear View",
            font=("Helvetica", 9),
            command=self.clear_points,
            padx=4,
            pady=0,
        )
        btn_clear.pack(side=tk.RIGHT, padx=4, pady=2)

        btn_close_poly = tk.Button(
            header,
            text="Close / Edit Mode",
            font=("Helvetica", 9),
            command=self.close_polygon,
            padx=4,
            pady=0,
        )
        btn_close_poly.pack(side=tk.RIGHT, padx=2, pady=2)

        btn_reset_zoom = tk.Button(
            header,
            text="Reset Zoom",
            font=("Helvetica", 9),
            command=self.reset_view,
            padx=4,
            pady=0,
        )
        btn_reset_zoom.pack(side=tk.RIGHT, padx=2, pady=2)

        # Drawing Canvas
        self.canvas = tk.Canvas(
            self,
            bg="#ffffff",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Margins for axis labels
        self.margin_left = 54
        self.margin_right = 20
        self.margin_top = 20
        self.margin_bottom = 36

        # Bind events
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<ButtonPress-1>", self._on_left_down)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_up)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)

        # Right-click (macOS uses Button-2 or Button-3 or Control-Button-1)
        self.canvas.bind("<ButtonPress-2>", self._on_right_click)
        self.canvas.bind("<ButtonPress-3>", self._on_right_click)
        self.canvas.bind("<Control-Button-1>", self._on_right_click)

        # Zoom with scroll wheel
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    # ------------------------------------------------------------------
    # Coordinate transforms (physical (u, v) <-> canvas pixel (px, py))
    # ------------------------------------------------------------------
    def _plot_rect(self):
        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)
        x0 = self.margin_left
        y0 = self.margin_top
        x1 = max(x0 + 20, w - self.margin_right)
        y1 = max(y0 + 20, h - self.margin_bottom)
        return x0, y0, x1, y1

    def uv_to_px(self, u, v):
        x0, y0, x1, y1 = self._plot_rect()
        u_min, u_max = self.u_range
        v_min, v_max = self.v_range
        px = x0 + (u - u_min) / (u_max - u_min) * (x1 - x0)
        py = y1 - (v - v_min) / (v_max - v_min) * (y1 - y0)
        return px, py

    def px_to_uv(self, px, py):
        x0, y0, x1, y1 = self._plot_rect()
        u_min, u_max = self.u_range
        v_min, v_max = self.v_range
        u = u_min + (px - x0) / max(1.0, (x1 - x0)) * (u_max - u_min)
        v = v_min + (y1 - py) / max(1.0, (y1 - y0)) * (v_max - v_min)
        return u, v

    def snap_uv(self, u, v, disable_snap=False):
        if not self.snap_enabled or disable_snap:
            return round(u, 4), round(v, 4)

        u_span = self.u_range[1] - self.u_range[0]
        v_span = self.v_range[1] - self.v_range[0]

        # Snap to key guide coordinates first if within 2.5% of span
        snapped_u = None
        for gu in self.u_guides:
            if abs(u - gu) <= 0.025 * u_span:
                snapped_u = gu
                break
        if snapped_u is None:
            # Snap to fine grid step
            fine_u = self.u_grid_step / 5.0
            snapped_u = round(u / fine_u) * fine_u

        snapped_v = None
        for gv in self.v_guides:
            if abs(v - gv) <= 0.03 * v_span:
                snapped_v = gv
                break
        if snapped_v is None:
            fine_v = self.v_grid_step / 5.0
            snapped_v = round(v / fine_v) * fine_v

        return round(snapped_u, 4), round(snapped_v, 4)

    # ------------------------------------------------------------------
    # Hit testing for vertices and edges
    # ------------------------------------------------------------------
    def _find_vertex_near(self, px, py, radius=10.0):
        best_i = None
        best_d2 = radius * radius
        for i, (u, v) in enumerate(self.points):
            vx, vy = self.uv_to_px(u, v)
            d2 = (px - vx) ** 2 + (py - vy) ** 2
            if d2 <= best_d2:
                best_d2 = d2
                best_i = i
        return best_i

    def _find_edge_near(self, px, py, tol=7.0):
        n = len(self.points)
        if n < 2:
            return None
        num_edges = n if (self.closed or n >= 3) else n - 1
        best_edge = None
        best_dist = tol
        for i in range(num_edges):
            j = (i + 1) % n
            x1, y1 = self.uv_to_px(*self.points[i])
            x2, y2 = self.uv_to_px(*self.points[j])
            dx, dy = x2 - x1, y2 - y1
            seg_len2 = dx * dx + dy * dy
            if seg_len2 < 1e-6:
                continue
            t = ((px - x1) * dx + (py - y1) * dy) / seg_len2
            if 0.15 <= t <= 0.85:
                proj_x = x1 + t * dx
                proj_y = y1 + t * dy
                dist = math.hypot(px - proj_x, py - proj_y)
                if dist <= best_dist:
                    best_dist = dist
                    best_edge = i
        return best_edge

    # ------------------------------------------------------------------
    # Mouse interaction handlers
    # ------------------------------------------------------------------
    def _on_motion(self, event):
        disable_snap = bool(event.state & 0x0001)  # Shift key disables snap
        u, v = self.px_to_uv(event.x, event.y)
        su, sv = self.snap_uv(u, v, disable_snap=disable_snap)
        self.cursor_uv = (su, sv)
        self.coord_lbl.config(
            text=f"{self.u_label}={su:g} μm, {self.v_label}={sv:g} μm"
        )

        v_idx = self._find_vertex_near(event.x, event.y)
        e_idx = None if v_idx is not None else self._find_edge_near(event.x, event.y)

        changed = (v_idx != self.hover_idx) or (e_idx != self.hover_edge_idx)
        self.hover_idx = v_idx
        self.hover_edge_idx = e_idx

        if v_idx is not None:
            self.canvas.config(cursor="hand2")
        elif e_idx is not None and self.closed:
            self.canvas.config(cursor="plus")
        else:
            self.canvas.config(cursor="crosshair")

        if changed or not self.closed:
            self.redraw()

    def _on_left_down(self, event):
        disable_snap = bool(event.state & 0x0001)
        u, v = self.px_to_uv(event.x, event.y)
        su, sv = self.snap_uv(u, v, disable_snap=disable_snap)

        # 1. Check if clicking an existing vertex
        v_idx = self._find_vertex_near(event.x, event.y)
        if v_idx is not None:
            # If user clicks the first vertex while drawing >= 3 points, close polygon AND allow dragging
            if not self.closed and v_idx == 0 and len(self.points) >= 3:
                self.closed = True
            self.selected_idx = v_idx
            self.dragging_idx = v_idx
            self._notify_point_selected()
            self.redraw()
            return

        # 2. If polygon is closed (or Shift held), clicking on an edge inserts a new point on that edge
        e_idx = self._find_edge_near(event.x, event.y)
        if e_idx is not None and (self.closed or bool(event.state & 0x0001)):
            insert_pos = e_idx + 1
            self.points.insert(insert_pos, [su, sv])
            self.selected_idx = insert_pos
            self.dragging_idx = insert_pos
            self._notify_point_selected()
            if self.on_geometry_changed:
                self.on_geometry_changed()
            self.redraw()
            return

        # 3. Otherwise, add a new connected point
        if self.closed:
            # Even if closed, if user clicks an edge it inserts; if they click in empty space,
            # insert along the nearest polygon edge so the polygon stays well-ordered!
            insert_pos = self._nearest_edge_insert_index(su, sv)
            self.points.insert(insert_pos, [su, sv])
            self.selected_idx = insert_pos
            self.dragging_idx = insert_pos
        else:
            self.points.append([su, sv])
            self.selected_idx = len(self.points) - 1
            self.dragging_idx = self.selected_idx

        self._notify_point_selected()
        if self.on_geometry_changed:
            self.on_geometry_changed()
        self.redraw()

    def _nearest_edge_insert_index(self, u, v):
        n = len(self.points)
        if n < 2:
            return n
        px, py = self.uv_to_px(u, v)
        best_idx = n
        best_dist = float("inf")
        for i in range(n):
            j = (i + 1) % n
            x1, y1 = self.uv_to_px(*self.points[i])
            x2, y2 = self.uv_to_px(*self.points[j])
            dx, dy = x2 - x1, y2 - y1
            seg_len2 = dx * dx + dy * dy
            if seg_len2 < 1e-6:
                dist = math.hypot(px - x1, py - y1)
            else:
                t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len2))
                dist = math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))
            if dist < best_dist:
                best_dist = dist
                best_idx = i + 1
        return best_idx

    def _on_left_drag(self, event):
        if self.dragging_idx is None:
            return
        x0, y0, x1, y1 = self._plot_rect()
        cx = max(x0, min(x1, event.x))
        cy = max(y0, min(y1, event.y))
        disable_snap = bool(event.state & 0x0001)
        u, v = self.px_to_uv(cx, cy)
        su, sv = self.snap_uv(u, v, disable_snap=disable_snap)
        self.points[self.dragging_idx] = [su, sv]
        self.cursor_uv = (su, sv)
        self.coord_lbl.config(
            text=f"{self.u_label}={su:g} μm, {self.v_label}={sv:g} μm"
        )
        self._notify_point_selected()
        if self.on_geometry_changed:
            self.on_geometry_changed()
        self.redraw()

    def _on_left_up(self, event):
        self.dragging_idx = None
        self.redraw()

    def _on_double_click(self, event):
        if len(self.points) >= 3:
            self.closed = True
            self.redraw()

    def _on_right_click(self, event):
        v_idx = self._find_vertex_near(event.x, event.y, radius=12.0)
        if v_idx is not None:
            del self.points[v_idx]
            if not self.points:
                self.selected_idx = None
                self.closed = False
            else:
                self.selected_idx = min(v_idx, len(self.points) - 1)
            self._notify_point_selected()
            if self.on_geometry_changed:
                self.on_geometry_changed()
            self.redraw()
        elif len(self.points) >= 3 and not self.closed:
            # Right-clicking empty space finishes/closes the current polygon
            self.closed = True
            self.redraw()

    def _on_mousewheel(self, event):
        # Zoom around cursor position
        u_c, v_c = self.px_to_uv(event.x, event.y)
        factor = 0.85 if event.delta > 0 else 1.18
        u_min, u_max = self.u_range
        v_min, v_max = self.v_range
        self.u_range = [
            u_c - (u_c - u_min) * factor,
            u_c + (u_max - u_c) * factor,
        ]
        self.v_range = [
            v_c - (v_c - v_min) * factor,
            v_c + (v_max - v_c) * factor,
        ]
        self.redraw()

    def _notify_point_selected(self):
        if self.on_point_selected:
            if self.selected_idx is not None and 0 <= self.selected_idx < len(self.points):
                pt = self.points[self.selected_idx]
                self.on_point_selected(self, self.selected_idx, pt[0], pt[1])
            else:
                self.on_point_selected(self, None, None, None)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def clear_points(self):
        self.points = []
        self.closed = False
        self.selected_idx = None
        self.dragging_idx = None
        self._notify_point_selected()
        if self.on_geometry_changed:
            self.on_geometry_changed()
        self.redraw()

    def close_polygon(self):
        if len(self.points) >= 3:
            self.closed = True
            self.redraw()

    def reset_view(self):
        self.u_range = list(self.default_u_range)
        self.v_range = list(self.default_v_range)
        self.redraw()

    def set_points(self, pts, closed=True):
        self.points = [[float(p[0]), float(p[1])] for p in pts]
        self.closed = closed and len(self.points) >= 3
        self.selected_idx = 0 if self.points else None
        self.redraw()

    def update_selected_point(self, new_u, new_v):
        if self.selected_idx is not None and 0 <= self.selected_idx < len(self.points):
            self.points[self.selected_idx] = [float(new_u), float(new_v)]
            if self.on_geometry_changed:
                self.on_geometry_changed()
            self.redraw()

    def delete_selected_point(self):
        if self.selected_idx is not None and 0 <= self.selected_idx < len(self.points):
            del self.points[self.selected_idx]
            if not self.points:
                self.selected_idx = None
                self.closed = False
            else:
                self.selected_idx = min(self.selected_idx, len(self.points) - 1)
            self._notify_point_selected()
            if self.on_geometry_changed:
                self.on_geometry_changed()
            self.redraw()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def redraw(self):
        self.canvas.delete("all")
        x0, y0, x1, y1 = self._plot_rect()

        # Plot area background & border
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#ffffff", outline="#adb5bd")

        # 1. Draw regular grid lines
        u_min, u_max = self.u_range
        v_min, v_max = self.v_range

        # Major grid along u
        step_u = self.u_grid_step
        start_u = math.ceil(u_min / step_u) * step_u
        u_val = start_u
        while u_val <= u_max + 1e-9:
            px, _ = self.uv_to_px(u_val, 0)
            if x0 <= px <= x1:
                color = "#ced4da" if abs(u_val) < 1e-9 else "#f1f3f5"
                width = 1.5 if abs(u_val) < 1e-9 else 1
                self.canvas.create_line(px, y0, px, y1, fill=color, width=width)
                self.canvas.create_text(
                    px,
                    y1 + 12,
                    text=f"{u_val:g}",
                    font=("Helvetica", 8),
                    fill="#495057",
                )
            u_val += step_u

        # Major grid along v
        step_v = self.v_grid_step
        start_v = math.ceil(v_min / step_v) * step_v
        v_val = start_v
        while v_val <= v_max + 1e-9:
            _, py = self.uv_to_px(0, v_val)
            if y0 <= py <= y1:
                color = "#ced4da" if abs(v_val) < 1e-9 else "#f1f3f5"
                width = 1.5 if abs(v_val) < 1e-9 else 1
                self.canvas.create_line(x0, py, x1, py, fill=color, width=width)
                self.canvas.create_text(
                    x0 - 6,
                    py,
                    text=f"{v_val:g}",
                    font=("Helvetica", 8),
                    fill="#495057",
                    anchor="e",
                )
            v_val += step_v

        # 2. Draw reference guide lines (key Slide 1 dimensions)
        for gu in self.u_guides:
            if u_min <= gu <= u_max and abs(gu) > 1e-9:
                px, _ = self.uv_to_px(gu, 0)
                self.canvas.create_line(
                    px, y0, px, y1, fill="#dee2e6", dash=(3, 3)
                )
                self.canvas.create_text(
                    px,
                    y0 - 8,
                    text=f"{gu:g}",
                    font=("Helvetica", 7),
                    fill="#868e96",
                )

        for gv in self.v_guides:
            if v_min <= gv <= v_max and abs(gv) > 1e-9:
                _, py = self.uv_to_px(0, gv)
                self.canvas.create_line(
                    x0, py, x1, py, fill="#dee2e6", dash=(3, 3)
                )

        # Axis titles
        self.canvas.create_text(
            (x0 + x1) / 2,
            y1 + 26,
            text=f"{self.u_label} (μm)",
            font=("Helvetica", 9, "bold"),
            fill="#212529",
        )
        self.canvas.create_text(
            14,
            (y0 + y1) / 2,
            text=f"{self.v_label}\n(μm)",
            font=("Helvetica", 9, "bold"),
            fill="#212529",
        )

        # 3. Draw polygon & connected segments
        n = len(self.points)
        px_pts = [self.uv_to_px(u, v) for u, v in self.points]

        if n >= 3:
            flat_coords = [coord for pt in px_pts for coord in pt]
            # Fill interior with InP gold (#FFC000) matching Slide 1
            self.canvas.create_polygon(
                *flat_coords,
                fill="#ffc000",
                outline="#b45309",
                width=2,
                stipple="",
            )
        elif n == 2:
            self.canvas.create_line(
                px_pts[0][0],
                px_pts[0][1],
                px_pts[1][0],
                px_pts[1][1],
                fill="#b45309",
                width=2,
            )

        # Highlight hovered edge when in edit mode
        if self.hover_edge_idx is not None and self.hover_edge_idx < n:
            i = self.hover_edge_idx
            j = (i + 1) % n
            self.canvas.create_line(
                px_pts[i][0],
                px_pts[i][1],
                px_pts[j][0],
                px_pts[j][1],
                fill="#0d6efd",
                width=3,
            )

        # Preview rubber-band line when still adding points
        if not self.closed and n >= 1 and self.cursor_uv is not None and self.hover_idx is None:
            cx, cy = self.uv_to_px(*self.cursor_uv)
            lx, ly = px_pts[-1]
            self.canvas.create_line(
                lx, ly, cx, cy, fill="#0d6efd", dash=(4, 2), width=1.5
            )
            if n >= 2:
                fx, fy = px_pts[0]
                self.canvas.create_line(
                    cx, cy, fx, fy, fill="#adb5bd", dash=(2, 3), width=1
                )

        # 4. Draw vertex handles and coordinates
        for i, (px, py) in enumerate(px_pts):
            is_sel = i == self.selected_idx
            is_hov = i == self.hover_idx
            r = 6 if (is_sel or is_hov) else 4.5
            fill_c = "#dc3545" if is_sel else ("#0d6efd" if is_hov else "#212529")
            outline_c = "#ffffff"
            self.canvas.create_oval(
                px - r,
                py - r,
                px + r,
                py + r,
                fill=fill_c,
                outline=outline_c,
                width=1.5,
            )
            if is_sel or is_hov:
                u, v = self.points[i]
                self.canvas.create_text(
                    px + 8,
                    py - 10,
                    text=f"P{i+1}({u:g}, {v:g})",
                    font=("Helvetica", 8, "bold"),
                    fill=fill_c,
                    anchor="w",
                )


class View3DCanvas(tk.Frame):
    """Interactive 3D viewport for displaying the reconstructed 3D waveguide geometry."""

    def __init__(self, parent):
        super().__init__(parent, bd=1, relief=tk.SOLID, bg="#f8f9fa")

        header = tk.Frame(self, bg="#e9ecef", height=26)
        header.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            header,
            text="  3D View (x-y-z)  —  Drag to Rotate, Scroll to Zoom",
            font=("Helvetica", 11, "bold"),
            bg="#e9ecef",
            fg="#212529",
            anchor="w",
        ).pack(side=tk.LEFT, padx=4, pady=2)

        btn_reset = tk.Button(
            header,
            text="Reset 3D Angle",
            font=("Helvetica", 9),
            command=self.reset_camera,
            padx=4,
            pady=0,
        )
        btn_reset.pack(side=tk.RIGHT, padx=4, pady=2)

        self.canvas = tk.Canvas(self, bg="#1e222a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Camera parameters
        self.azim = -55.0  # degrees
        self.elev = 26.0   # degrees
        self.zoom = 1.0
        self._drag_prev = None

        # Reconstructed 3D data
        # List of 3D prism segments or general extruded polyhedron faces
        self.faces_3d = []  # Each item: (list of (x, y, z) vertices, face_type)
        self.bbox_3d = None
        self.summary_text = ""

        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def reset_camera(self):
        self.azim = -55.0
        self.elev = 26.0
        self.zoom = 1.0
        self.redraw()

    def clear_3d(self):
        self.faces_3d = []
        self.bbox_3d = None
        self.summary_text = ""
        self.redraw()

    def set_geometry(self, faces_3d, bbox_3d, summary_text=""):
        self.faces_3d = faces_3d
        self.bbox_3d = bbox_3d
        self.summary_text = summary_text
        self.redraw()

    def _on_mouse_down(self, event):
        self._drag_prev = (event.x, event.y)

    def _on_mouse_drag(self, event):
        if self._drag_prev is None:
            return
        dx = event.x - self._drag_prev[0]
        dy = event.y - self._drag_prev[1]
        self._drag_prev = (event.x, event.y)
        self.azim += dx * 0.6
        self.elev = max(-85.0, min(85.0, self.elev + dy * 0.6))
        self.redraw()

    def _on_mouse_up(self, event):
        self._drag_prev = None

    def _on_mousewheel(self, event):
        factor = 1.12 if event.delta > 0 else 0.89
        self.zoom = max(0.3, min(4.0, self.zoom * factor))
        self.redraw()

    def _project_point(self, x, y, z, cx, cy, scale):
        """Normalize physical (x, y, z) to visual box [-1, 1] with schematic aspect ratio and project."""
        if self.bbox_3d is None:
            nx, ny, nz = x, y, z
        else:
            xmin, xmax, ymin, ymax, zmin, zmax = self.bbox_3d
            xmid = 0.5 * (xmin + xmax)
            ymid = 0.5 * (ymin + ymax)
            zmid = 0.5 * (zmin + zmax)
            dx = max(xmax - xmin, 1e-6)
            dy = max(ymax - ymin, 1e-6)
            dz = max(zmax - zmin, 1e-6)
            # Normalized schematic proportions so x (long), y (width), and z (thin layer)
            # are all clearly visible in 3D
            nx = (x - xmid) / (dx * 0.5) * 1.35
            ny = (y - ymid) / (dy * 0.5) * 0.55
            nz = (z - zmid) / (dz * 0.5) * 0.22

        az = math.radians(self.azim)
        el = math.radians(self.elev)
        cos_a, sin_a = math.cos(az), math.sin(az)
        cos_e, sin_e = math.cos(el), math.sin(el)

        # Rotate around Z by azim, then tilt by elev
        rx = nx * cos_a - ny * sin_a
        ry = nx * sin_a + ny * cos_a
        rz = nz

        px_3d = rx
        py_3d = -ry * sin_e + rz * cos_e
        depth = ry * cos_e + rz * sin_e

        # Perspective factor
        persp = 1.0 / max(0.4, 3.2 - depth * 0.35) * 2.8
        sx = cx + px_3d * scale * self.zoom * persp
        sy = cy - py_3d * scale * self.zoom * persp
        return sx, sy, depth

    def redraw(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)
        cx = w * 0.5
        cy = h * 0.52
        scale = min(w, h) * 0.31

        if not self.faces_3d:
            self.canvas.create_text(
                cx,
                cy - 12,
                text="No 3D Geometry Generated Yet",
                font=("Helvetica", 13, "bold"),
                fill="#ced4da",
            )
            self.canvas.create_text(
                cx,
                cy + 14,
                text="Draw profiles in Top (x-y), Side (x-z), and Front (y-z) views,\nthen click '2. Generate geometry'.",
                font=("Helvetica", 10),
                fill="#868e96",
                justify=tk.CENTER,
            )
            self._draw_axes_triad(w, h)
            return

        # Draw 3D bounding wireframe box & dimension labels
        xmin, xmax, ymin, ymax, zmin, zmax = self.bbox_3d
        box_corners = [
            (xmin, ymin, zmin),
            (xmax, ymin, zmin),
            (xmax, ymax, zmin),
            (xmin, ymax, zmin),
            (xmin, ymin, zmax),
            (xmax, ymin, zmax),
            (xmax, ymax, zmax),
            (xmin, ymax, zmax),
        ]
        proj_corners = [self._project_point(*pt, cx, cy, scale) for pt in box_corners]
        box_edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        for i, j in box_edges:
            self.canvas.create_line(
                proj_corners[i][0],
                proj_corners[i][1],
                proj_corners[j][0],
                proj_corners[j][1],
                fill="#3b4252",
                dash=(2, 2),
            )

        # Depth-sort faces (Painter's algorithm)
        rendered_faces = []
        for verts, face_kind in self.faces_3d:
            proj = [self._project_point(vx, vy, vz, cx, cy, scale) for vx, vy, vz in verts]
            avg_depth = sum(p[2] for p in proj) / len(proj)
            rendered_faces.append((avg_depth, proj, face_kind))

        rendered_faces.sort(key=lambda item: item[0])

        # Draw sorted faces
        for _, proj, face_kind in rendered_faces:
            coords = [c for pt in proj for c in (pt[0], pt[1])]
            if face_kind == "top":
                fill_color = "#ffd43b"
                edge_color = "#8c6d1f"
            elif face_kind == "bottom":
                fill_color = "#cca000"
                edge_color = "#665000"
            elif face_kind == "end":
                fill_color = "#e6ac00"
                edge_color = "#5c4500"
            else:
                fill_color = "#f59f00"
                edge_color = "#704800"

            self.canvas.create_polygon(
                *coords,
                fill=fill_color,
                outline=edge_color,
                width=1.2,
            )

        # Axis dimension annotations on bounding box
        p_x0 = proj_corners[0]
        p_x1 = proj_corners[1]
        self.canvas.create_text(
            0.5 * (p_x0[0] + p_x1[0]),
            0.5 * (p_x0[1] + p_x1[1]) + 14,
            text=f"Δx = {xmax - xmin:g} μm",
            font=("Helvetica", 9, "bold"),
            fill="#74c0fc",
        )
        p_y1 = proj_corners[2]
        self.canvas.create_text(
            0.5 * (p_x1[0] + p_y1[0]) + 18,
            0.5 * (p_x1[1] + p_y1[1]) + 8,
            text=f"Δy = {ymax - ymin:g} μm",
            font=("Helvetica", 9, "bold"),
            fill="#63e6be",
        )
        p_z1 = proj_corners[5]
        self.canvas.create_text(
            0.5 * (p_x1[0] + p_z1[0]) + 24,
            0.5 * (p_x1[1] + p_z1[1]),
            text=f"Δz = {(zmax - zmin)*1000:g} nm",
            font=("Helvetica", 9, "bold"),
            fill="#ffa8a8",
        )

        # Info banner at top-left of 3D canvas
        if self.summary_text:
            self.canvas.create_text(
                12,
                10,
                text=self.summary_text,
                font=("Helvetica", 9),
                fill="#e9ecef",
                anchor="nw",
            )

        self._draw_axes_triad(w, h)

    def _draw_axes_triad(self, w, h):
        ox, oy = 52, h - 42
        axis_len = 28
        az = math.radians(self.azim)
        el = math.radians(self.elev)
        cos_a, sin_a = math.cos(az), math.sin(az)
        cos_e, sin_e = math.cos(el), math.sin(el)

        axes = [
            ("x", (1, 0, 0), "#74c0fc"),
            ("y", (0, 1, 0), "#63e6be"),
            ("z", (0, 0, 1), "#ffa8a8"),
        ]
        for label, (ux, uy, uz), color in axes:
            rx = ux * cos_a - uy * sin_a
            ry = ux * sin_a + uy * cos_a
            rz = uz
            sx = ox + rx * axis_len
            sy = oy - (-ry * sin_e + rz * cos_e) * axis_len
            self.canvas.create_line(ox, oy, sx, sy, fill=color, width=2, arrow=tk.LAST)
            self.canvas.create_text(
                sx + (sx - ox) * 0.28,
                sy + (sy - oy) * 0.28,
                text=label,
                font=("Helvetica", 9, "bold"),
                fill=color,
            )


class LumericalGeometryApp:
    """Main application window combining the 4 views and Lumerical .lsf export."""

    def __init__(self, root):
        self.root = root
        self.root.title("Ansys Lumerical 3D Geometry Generator — Multi-View Editor")
        self.root.geometry("1280x840")
        self.root.minsize(980, 680)

        self.active_view = None
        self.reconstructed_segments = []
        self.reconstructed_xy_poly = []
        self.reconstructed_z_span = (-0.125, 0.125)

        self._build_ui()

    def _build_ui(self):
        # ==================================================================
        # Top Control Toolbar
        # ==================================================================
        toolbar = tk.Frame(self.root, bg="#dee2e6", bd=1, relief=tk.RAISED, padx=8, pady=6)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        # Primary required buttons:
        # 1. Generate file
        # 2. Generate geometry
        self.btn_gen_geom = tk.Button(
            toolbar,
            text="2. Generate geometry",
            font=("Helvetica", 11, "bold"),
            command=self.generate_geometry,
            padx=12,
            pady=4,
        )
        self.btn_gen_geom.pack(side=tk.LEFT, padx=6)

        self.btn_gen_file = tk.Button(
            toolbar,
            text="1. Generate file",
            font=("Helvetica", 11, "bold"),
            command=self.generate_file,
            padx=12,
            pady=4,
        )
        self.btn_gen_file.pack(side=tk.LEFT, padx=6)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        # Preset & Reset buttons
        btn_preset = tk.Button(
            toolbar,
            text="Load Slide 1 Preset",
            font=("Helvetica", 10),
            command=self.load_slide1_preset,
            padx=8,
            pady=3,
        )
        btn_preset.pack(side=tk.LEFT, padx=4)

        btn_clear_all = tk.Button(
            toolbar,
            text="Clear All Views",
            font=("Helvetica", 10),
            command=self.clear_all,
            padx=8,
            pady=3,
        )
        btn_clear_all.pack(side=tk.LEFT, padx=4)

        self.snap_var = tk.BooleanVar(value=True)
        chk_snap = tk.Checkbutton(
            toolbar,
            text="Snap to Guides/Grid",
            variable=self.snap_var,
            command=self._toggle_snap,
            bg="#dee2e6",
            font=("Helvetica", 10),
        )
        chk_snap.pack(side=tk.LEFT, padx=6)

        btn_mirror_y = tk.Button(
            toolbar,
            text="Mirror Top (x-y)",
            font=("Helvetica", 10),
            command=self.mirror_xy_top_to_bottom,
            padx=6,
            pady=3,
        )
        btn_mirror_y.pack(side=tk.LEFT, padx=4)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        # Selected Point Coordinate Editor (for exact numerical modification)
        pt_frame = tk.Frame(toolbar, bg="#dee2e6")
        pt_frame.pack(side=tk.LEFT, padx=4)

        self.lbl_sel_pt = tk.Label(
            pt_frame,
            text="Selected Point: None",
            font=("Helvetica", 9, "bold"),
            bg="#dee2e6",
            width=20,
            anchor="w",
        )
        self.lbl_sel_pt.pack(side=tk.LEFT, padx=2)

        tk.Label(pt_frame, text="Coord 1:", font=("Helvetica", 9), bg="#dee2e6").pack(side=tk.LEFT)
        self.ent_u = tk.Entry(pt_frame, width=8, font=("Helvetica", 9))
        self.ent_u.pack(side=tk.LEFT, padx=2)
        self.ent_u.bind("<Return>", lambda e: self.apply_point_edit())

        tk.Label(pt_frame, text="Coord 2:", font=("Helvetica", 9), bg="#dee2e6").pack(side=tk.LEFT)
        self.ent_v = tk.Entry(pt_frame, width=8, font=("Helvetica", 9))
        self.ent_v.pack(side=tk.LEFT, padx=2)
        self.ent_v.bind("<Return>", lambda e: self.apply_point_edit())

        btn_apply_pt = tk.Button(
            pt_frame,
            text="Modify Point",
            font=("Helvetica", 9),
            command=self.apply_point_edit,
            padx=5,
            pady=1,
        )
        btn_apply_pt.pack(side=tk.LEFT, padx=3)

        btn_del_pt = tk.Button(
            pt_frame,
            text="Delete Point",
            font=("Helvetica", 9),
            command=self.delete_selected_point,
            padx=5,
            pady=1,
        )
        btn_del_pt.pack(side=tk.LEFT, padx=2)

        # ==================================================================
        # Main 2x2 Quadrant Grid
        #   (0, 0) Top View (x-y)     |  (0, 1) 3D View (x-y-z)
        #   --------------------------+--------------------------
        #   (1, 0) Side View (x-z)    |  (1, 1) Front View (y-z)
        # ==================================================================
        grid_frame = tk.Frame(self.root, bg="#adb5bd")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        grid_frame.columnconfigure(0, weight=1, uniform="col")
        grid_frame.columnconfigure(1, weight=1, uniform="col")
        grid_frame.rowconfigure(0, weight=1, uniform="row")
        grid_frame.rowconfigure(1, weight=1, uniform="row")

        # Key guide coordinates from Slide 1
        x_guides = [-300.0, -110.0, -100.0, 0.0, 100.0, 110.0, 300.0]
        y_guides = [-0.75, -0.25, -0.05, 0.0, 0.05, 0.25, 0.75]
        z_guides = [-0.125, 0.0, 0.125]

        # 1. Top-Left: Top View (x-y)
        self.view_xy = OrthoCanvas2D(
            grid_frame,
            title="Top view (x-y)",
            u_label="x",
            v_label="y",
            u_range=[-340.0, 340.0],
            v_range=[-1.05, 1.05],
            u_guides=x_guides,
            v_guides=y_guides,
            u_grid_step=100.0,
            v_grid_step=0.25,
            on_point_selected=self._on_point_selected,
        )
        self.view_xy.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # 2. Bottom-Left: Side View (x-z)
        self.view_xz = OrthoCanvas2D(
            grid_frame,
            title="Side view / Cross section (x-z)",
            u_label="x",
            v_label="z",
            u_range=[-340.0, 340.0],
            v_range=[-0.28, 0.28],
            u_guides=x_guides,
            v_guides=z_guides,
            u_grid_step=100.0,
            v_grid_step=0.1,
            on_point_selected=self._on_point_selected,
        )
        self.view_xz.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        # 3. Top-Right: 3D View
        self.view_3d = View3DCanvas(grid_frame)
        self.view_3d.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        # 4. Bottom-Right: Front View (y-z)
        self.view_yz = OrthoCanvas2D(
            grid_frame,
            title="Front view / Cross section (y-z)",
            u_label="y",
            v_label="z",
            u_range=[-1.05, 1.05],
            v_range=[-0.28, 0.28],
            u_guides=y_guides,
            v_guides=z_guides,
            u_grid_step=0.25,
            v_grid_step=0.1,
            on_point_selected=self._on_point_selected,
        )
        self.view_yz.grid(row=1, column=1, sticky="nsew", padx=2, pady=2)

        # ==================================================================
        # Status Bar
        # ==================================================================
        status_frame = tk.Frame(self.root, bg="#e9ecef", bd=1, relief=tk.SUNKEN)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_lbl = tk.Label(
            status_frame,
            text=(
                "Instructions: Left-click in Top (x-y), Side (x-z), and Front (y-z) to draw connected points. "
                "Drag any vertex to modify it. Click '2. Generate geometry' to build 3D view, and '1. Generate file' to save .lsf."
            ),
            font=("Helvetica", 9),
            bg="#e9ecef",
            fg="#212529",
            anchor="w",
            padx=8,
            pady=3,
        )
        self.status_lbl.pack(fill=tk.X)

        # Keyboard shortcut to delete selected vertex
        self.root.bind("<BackSpace>", lambda e: self._handle_delete_key())
        self.root.bind("<Delete>", lambda e: self._handle_delete_key())

    def _handle_delete_key(self):
        # Avoid intercepting BackSpace when typing in Entry widgets
        focused = self.root.focus_get()
        if isinstance(focused, tk.Entry):
            return
        self.delete_selected_point()

    def _toggle_snap(self):
        snap = self.snap_var.get()
        self.view_xy.snap_enabled = snap
        self.view_xz.snap_enabled = snap
        self.view_yz.snap_enabled = snap

    def _on_point_selected(self, view_obj, idx, u, v):
        self.active_view = view_obj
        # Deselect in other views for clarity
        for v_canvas in (self.view_xy, self.view_xz, self.view_yz):
            if v_canvas is not view_obj and v_canvas.selected_idx is not None:
                v_canvas.selected_idx = None
                v_canvas.redraw()

        if idx is None:
            self.lbl_sel_pt.config(text="Selected Point: None")
            self.ent_u.delete(0, tk.END)
            self.ent_v.delete(0, tk.END)
        else:
            self.lbl_sel_pt.config(
                text=f"{view_obj.title.split()[0]} P{idx+1} ({view_obj.u_label},{view_obj.v_label}):"
            )
            self.ent_u.delete(0, tk.END)
            self.ent_u.insert(0, f"{u:g}")
            self.ent_v.delete(0, tk.END)
            self.ent_v.insert(0, f"{v:g}")

    def apply_point_edit(self):
        if self.active_view is None:
            return
        try:
            new_u = float(self.ent_u.get())
            new_v = float(self.ent_v.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric coordinates.")
            return
        self.active_view.update_selected_point(new_u, new_v)
        self.status_lbl.config(
            text=f"Updated point in {self.active_view.title} to ({new_u:g}, {new_v:g}) μm. Click '2. Generate geometry' to refresh 3D view."
        )

    def delete_selected_point(self):
        if self.active_view is not None:
            self.active_view.delete_selected_point()

    def clear_all(self):
        self.view_xy.clear_points()
        self.view_xz.clear_points()
        self.view_yz.clear_points()
        self.view_3d.clear_3d()
        self.reconstructed_segments = []
        self.reconstructed_xy_poly = []
        self.status_lbl.config(text="Cleared all views. Draw connected points in (x-y), (x-z), and (y-z).")

    def mirror_xy_top_to_bottom(self):
        """Mirrors the upper profile points (y > 0) in Top view (x-y) across y = 0 to form a symmetric waveguide."""
        pts = self.view_xy.points
        if len(pts) < 2:
            messagebox.showinfo(
                "Mirror Top (x-y)",
                "Draw at least 2 connected points along the upper boundary (y > 0) in Top view (x-y) first.",
            )
            return
        # Keep upper half points (or all points if user only drew one side) sorted by x
        upper = [p for p in pts if p[1] >= 0]
        if len(upper) < 2:
            upper = list(pts)
        upper_sorted = sorted(upper, key=lambda p: p[0])
        lower_sorted = [[p[0], -abs(p[1])] for p in upper_sorted]
        upper_clean = [[p[0], abs(p[1])] for p in reversed(upper_sorted)]
        self.view_xy.set_points(lower_sorted + upper_clean, closed=True)
        self.status_lbl.config(
            text="Mirrored Top view (x-y) profile symmetrically across y = 0."
        )

    def load_slide1_preset(self):
        """Loads the exact Slide 1 geometry into the three orthographic 2D views."""
        # Top view (x-y): 12-vertex symmetric two-stage tapered InP waveguide
        xy_pts = [
            [-300.0, -0.05],
            [-110.0, -0.25],
            [-100.0, -0.75],
            [100.0, -0.75],
            [110.0, -0.25],
            [300.0, -0.05],
            [300.0, 0.05],
            [110.0, 0.25],
            [100.0, 0.75],
            [-100.0, 0.75],
            [-110.0, 0.25],
            [-300.0, 0.05],
        ]
        # Side view (x-z): 600 um long, 250 nm (0.25 um) thick
        xz_pts = [
            [-300.0, -0.125],
            [300.0, -0.125],
            [300.0, 0.125],
            [-300.0, 0.125],
        ]
        # Front view (y-z): 1.5 um wide, 250 nm (0.25 um) thick
        yz_pts = [
            [-0.75, -0.125],
            [0.75, -0.125],
            [0.75, 0.125],
            [-0.75, 0.125],
        ]
        self.view_xy.set_points(xy_pts, closed=True)
        self.view_xz.set_points(xz_pts, closed=True)
        self.view_yz.set_points(yz_pts, closed=True)
        self.status_lbl.config(
            text="Loaded Slide 1 geometry into Top (x-y), Side (x-z), and Front (y-z) views. Drag any vertex to modify, or click '2. Generate geometry'."
        )

    # ==================================================================
    # 3D Geometry Reconstruction from the Three 2D Views
    # ==================================================================
    @staticmethod
    def _vertical_slice_bounds(poly_pts, u_query):
        """Finds [v_min, v_max] of a 2D polygon at horizontal coordinate u_query."""
        n = len(poly_pts)
        v_hits = []
        tol = 1e-7
        for i in range(n):
            u1, v1 = poly_pts[i]
            u2, v2 = poly_pts[(i + 1) % n]
            if abs(u1 - u_query) <= tol:
                v_hits.append(v1)
            if abs(u2 - u_query) <= tol:
                v_hits.append(v2)
            if (u1 - u_query) * (u2 - u_query) < 0:
                t = (u_query - u1) / (u2 - u1)
                v_hits.append(v1 + t * (v2 - v1))
        if not v_hits:
            # Fallback to nearest vertex in u
            nearest_v = [v for u, v in poly_pts]
            return min(nearest_v), max(nearest_v)
        return min(v_hits), max(v_hits)

    def _decompose_longitudinal_segments(self, xy_pts, xz_pts, yz_pts):
        """
        Combines the drawn Top (x-y), Side (x-z), and Front (y-z) polygons into
        3D longitudinal segments and faces.
        """
        # 1. Extract z bounds from Side (x-z) and Front (y-z)
        xz_zs = [p[1] for p in xz_pts]
        yz_zs = [p[1] for p in yz_pts]
        # Average/combine z bounds from xz and yz views (or use xz local z envelope)
        z_min_global = 0.5 * (min(xz_zs) + min(yz_zs))
        z_max_global = 0.5 * (max(xz_zs) + max(yz_zs))
        if abs(z_max_global - z_min_global) < 1e-6:
            z_min_global, z_max_global = -0.125, 0.125

        # Also check if Front view (y-z) scales the overall y width relative to Top view (x-y)
        xy_ys = [p[1] for p in xy_pts]
        xy_ymax_span = max(xy_ys) - min(xy_ys)
        yz_ys = [p[0] for p in yz_pts]
        yz_ymax_span = max(yz_ys) - min(yz_ys)

        # Unique sorted x stations from Top view (x-y), clustering points within 0.25 um
        raw_xs = sorted(p[0] for p in xy_pts)
        x_stations = []
        for x_val in raw_xs:
            if not x_stations or abs(x_val - x_stations[-1]) > 0.25:
                x_stations.append(x_val)
            else:
                # Average nearly-identical x coordinates
                x_stations[-1] = 0.5 * (x_stations[-1] + x_val)

        # Map x-z polygon x-range onto x_stations so local z(x) variations in Side view are respected
        xz_xmin = min(p[0] for p in xz_pts)
        xz_xmax = max(p[0] for p in xz_pts)
        xy_xmin = x_stations[0]
        xy_xmax = x_stations[-1]

        def z_bounds_at_x(x_val):
            if xz_xmax - xz_xmin > 1e-6 and xy_xmax - xy_xmin > 1e-6:
                u_mapped = xz_xmin + (x_val - xy_xmin) / (xy_xmax - xy_xmin) * (xz_xmax - xz_xmin)
                zb, zt = self._vertical_slice_bounds(xz_pts, u_mapped)
                # Scale by yz view z-span if user modified Front view z
                xz_span = max(xz_zs) - min(xz_zs)
                yz_span = max(yz_zs) - min(yz_zs)
                if xz_span > 1e-6 and yz_span > 1e-6:
                    z_center = 0.5 * (zb + zt)
                    half_h = 0.5 * (zt - zb) * (yz_span / xz_span)
                    return z_center - half_h, z_center + half_h
                return zb, zt
            return z_min_global, z_max_global

        segments = []
        faces_3d = []

        for i in range(len(x_stations) - 1):
            x0 = x_stations[i]
            x1 = x_stations[i + 1]
            if x1 - x0 < 1e-5:
                continue

            # Slightly inset query points to handle vertical steps cleanly
            eps = min(1e-4, 0.01 * (x1 - x0))
            y0_bot, y0_top = self._vertical_slice_bounds(xy_pts, x0 + eps)
            y1_bot, y1_top = self._vertical_slice_bounds(xy_pts, x1 - eps)

            z0_bot, z0_top = z_bounds_at_x(x0 + eps)
            z1_bot, z1_top = z_bounds_at_x(x1 - eps)

            seg = {
                "x0": round(x0, 4),
                "x1": round(x1, 4),
                "y0_bot": round(y0_bot, 4),
                "y0_top": round(y0_top, 4),
                "y1_bot": round(y1_bot, 4),
                "y1_top": round(y1_top, 4),
                "z0_bot": round(z0_bot, 4),
                "z0_top": round(z0_top, 4),
                "z1_bot": round(z1_bot, 4),
                "z1_top": round(z1_top, 4),
            }
            segments.append(seg)

            # 8 corners of the hexahedral segment
            b0 = (x0, y0_bot, z0_bot)
            b1 = (x1, y1_bot, z1_bot)
            b2 = (x1, y1_top, z1_bot)
            b3 = (x0, y0_top, z0_bot)

            t0 = (x0, y0_bot, z0_top)
            t1 = (x1, y1_bot, z1_top)
            t2 = (x1, y1_top, z1_top)
            t3 = (x0, y0_top, z0_top)

            faces_3d.append(([b0, b1, b2, b3], "bottom"))
            faces_3d.append(([t0, t1, t2, t3], "top"))
            faces_3d.append(([b0, b1, t1, t0], "side"))
            faces_3d.append(([b3, b2, t2, t3], "side"))
            faces_3d.append(([b0, b3, t3, t0], "end"))
            faces_3d.append(([b1, b2, t2, t1], "end"))

        all_x = [v[0] for f, _ in faces_3d for v in f]
        all_y = [v[1] for f, _ in faces_3d for v in f]
        all_z = [v[2] for f, _ in faces_3d for v in f]
        bbox_3d = (
            min(all_x),
            max(all_x),
            min(all_y),
            max(all_y),
            min(all_z),
            max(all_z),
        )
        return segments, faces_3d, bbox_3d

    def generate_geometry(self):
        """Validates the 2D views, reconstructs the 3D solid, and renders it in the 3D view."""
        missing = []
        if len(self.view_xy.points) < 3:
            missing.append("Top view (x-y)")
        if len(self.view_xz.points) < 3:
            missing.append("Side view (x-z)")
        if len(self.view_yz.points) < 3:
            missing.append("Front view (y-z)")

        if missing:
            messagebox.showwarning(
                "Incomplete Views",
                "Please draw connected polygons (at least 3 points) in all three 2D views before generating the 3D geometry.\n\n"
                f"Currently missing ≥3 points in:\n  • " + "\n  • ".join(missing)
                + "\n\nTip: You can also click 'Load Slide 1 Preset' to load the example geometry.",
            )
            return

        # Mark all 3 views as closed polygons so subsequent clicks edit nicely
        self.view_xy.close_polygon()
        self.view_xz.close_polygon()
        self.view_yz.close_polygon()

        segments, faces_3d, bbox_3d = self._decompose_longitudinal_segments(
            self.view_xy.points,
            self.view_xz.points,
            self.view_yz.points,
        )

        self.reconstructed_segments = segments
        self.reconstructed_xy_poly = [list(p) for p in self.view_xy.points]
        self.reconstructed_z_span = (bbox_3d[4], bbox_3d[5])

        xmin, xmax, ymin, ymax, zmin, zmax = bbox_3d
        summary = (
            f"Material: InP  |  Sections: {len(segments)}\n"
            f"x: [{xmin:g}, {xmax:g}] μm (L = {xmax - xmin:g} μm)\n"
            f"y: [{ymin:g}, {ymax:g}] μm (W_max = {ymax - ymin:g} μm)\n"
            f"z: [{zmin:g}, {zmax:g}] μm (T = {(zmax - zmin)*1000:g} nm)"
        )
        self.view_3d.set_geometry(faces_3d, bbox_3d, summary_text=summary)
        self.status_lbl.config(
            text=f"3D geometry generated ({len(segments)} longitudinal section(s), L={xmax-xmin:g} μm, W_max={ymax-ymin:g} μm, T={(zmax-zmin)*1000:g} nm)."
        )

    # ==================================================================
    # Ansys Lumerical (.lsf) Script Generation
    # ==================================================================
    def build_lsf_content(self):
        """Builds the Ansys Lumerical .lsf script string from the reconstructed 3D geometry."""
        if not self.reconstructed_segments:
            self.generate_geometry()
            if not self.reconstructed_segments:
                return None

        z_min, z_max = self.reconstructed_z_span
        t_z_nm = round((z_max - z_min) * 1000.0, 4)
        z_center_um = round(0.5 * (z_min + z_max), 6)

        lines = [
            "# =========================================================================",
            "# Ansys Lumerical Script (.lsf)",
            "# 3D Geometry Generated from Interactive Multi-View Geometry Builder",
            "#",
            "# Coordinate System:",
            "#   x : Propagation / longitudinal direction",
            "#   y : Lateral / width direction (in-plane)",
            "#   z : Vertical / thickness direction (out-of-plane)",
            "# =========================================================================",
            "",
            "clear;",
            "deleteall;",
            "",
            "# -------------------------------------------------------------------------",
            "# 1. Units & Global Parameters (SI units: meters)",
            "# -------------------------------------------------------------------------",
            "um = 1e-6;",
            "nm = 1e-9;",
            "",
            f"t_z      = {t_z_nm:g} * nm;   # Layer thickness ({(z_max - z_min):g} um)",
            f"z_center = {z_center_um:g} * um;   # Center z-coordinate",
            "",
            "# Material configuration",
            'mat_name = "InP - Palik";',
            "if (!materialexists(mat_name)) {",
            '    if (materialexists("InP")) {',
            '        mat_name = "InP";',
            "    } else {",
            '        mat_name = addmaterial("(n,k) Material");',
            '        setmaterial(mat_name, "name", "InP");',
            '        setmaterial("InP", "Refractive Index", 3.17);',
            '        mat_name = "InP";',
            "    }",
            "}",
            "",
            "# Toggle: 0 = Individual longitudinal sections, 1 = Unified extruded polygon",
            "use_single_polygon = 0;",
            "",
            "# -------------------------------------------------------------------------",
            "# 2. Build 3D Geometry inside 'InP_Structure' Group",
            "# -------------------------------------------------------------------------",
            "addstructuregroup;",
            'set("name", "InP_Structure");',
            'set("x", 0);',
            'set("y", 0);',
            'set("z", 0);',
            "",
            "if (use_single_polygon == 1) {",
            "    V_all = [",
        ]

        for idx, (vx, vy) in enumerate(self.reconstructed_xy_poly):
            sep = ";" if idx < len(self.reconstructed_xy_poly) - 1 else ""
            lines.append(f"        {vx:g} * um, {vy:g} * um{sep}")

        lines.extend(
            [
                "    ];",
                "    addpoly;",
                '    set("name", "InP_waveguide_full");',
                '    set("x", 0);',
                '    set("y", 0);',
                '    set("z", z_center);',
                '    set("z span", t_z);',
                '    set("vertices", V_all);',
                '    set("material", mat_name);',
                '    addtogroup("InP_Structure");',
                "} else {",
            ]
        )

        for idx, seg in enumerate(self.reconstructed_segments, start=1):
            x0, x1 = seg["x0"], seg["x1"]
            y0_b, y0_t = seg["y0_bot"], seg["y0_top"]
            y1_b, y1_t = seg["y1_bot"], seg["y1_top"]
            seg_len = round(x1 - x0, 4)
            w0 = round(y0_t - y0_b, 4)
            w1 = round(y1_t - y1_b, 4)
            seg_z_c = round(0.25 * (seg["z0_bot"] + seg["z0_top"] + seg["z1_bot"] + seg["z1_top"]), 6)
            seg_z_span_nm = round(
                0.5 * ((seg["z0_top"] - seg["z0_bot"]) + (seg["z1_top"] - seg["z1_bot"])) * 1000.0,
                4,
            )

            is_rect = (
                abs(y0_b - y1_b) < 1e-4
                and abs(y0_t - y1_t) < 1e-4
            )

            if is_rect:
                x_mid = round(0.5 * (x0 + x1), 4)
                y_mid = round(0.5 * (y0_b + y0_t), 4)
                lines.extend(
                    [
                        f"    # Section ({idx}): Straight waveguide x=[{x0:g}, {x1:g}] um, width={w0:g} um",
                        "    addrect;",
                        f'    set("name", "section_{idx}_straight_{seg_len:g}um");',
                        f'    set("x", {x_mid:g} * um);',
                        f'    set("x span", {seg_len:g} * um);',
                        f'    set("y", {y_mid:g} * um);',
                        f'    set("y span", {w0:g} * um);',
                        f'    set("z", {seg_z_c:g} * um);',
                        f'    set("z span", {seg_z_span_nm:g} * nm);',
                        '    set("material", mat_name);',
                        '    addtogroup("InP_Structure");',
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"    # Section ({idx}): Taper x=[{x0:g}, {x1:g}] um, width={w0:g} um -> {w1:g} um",
                        f"    V_sec_{idx} = [",
                        f"        {x0:g} * um, {y0_b:g} * um;",
                        f"        {x1:g} * um, {y1_b:g} * um;",
                        f"        {x1:g} * um, {y1_t:g} * um;",
                        f"        {x0:g} * um, {y0_t:g} * um",
                        "    ];",
                        "    addpoly;",
                        f'    set("name", "section_{idx}_taper_{seg_len:g}um");',
                        '    set("x", 0);',
                        '    set("y", 0);',
                        f'    set("z", {seg_z_c:g} * um);',
                        f'    set("z span", {seg_z_span_nm:g} * nm);',
                        f'    set("vertices", V_sec_{idx});',
                        '    set("material", mat_name);',
                        '    addtogroup("InP_Structure");',
                        "",
                    ]
                )

        x_total = round(
            self.reconstructed_segments[-1]["x1"] - self.reconstructed_segments[0]["x0"],
            4,
        )
        w_max = round(
            max(
                max(s["y0_top"] - s["y0_bot"], s["y1_top"] - s["y1_bot"])
                for s in self.reconstructed_segments
            ),
            4,
        )
        lines.extend(
            [
                "}",
                "",
                f'?"3D InP structure successfully generated (Total x-length: {x_total:g} um, max y-width: {w_max:g} um, z-thickness: {t_z_nm:g} nm).";',
                "",
            ]
        )
        return "\n".join(lines)

    def generate_file(self):
        """Generates the Ansys Lumerical (.lsf) file from the current geometry."""
        lsf_text = self.build_lsf_content()
        if not lsf_text:
            return

        default_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Ansys Lumerical Script (.lsf)",
            initialdir=default_dir,
            initialfile="generate_structure.lsf",
            defaultextension=".lsf",
            filetypes=[("Lumerical Script Files", "*.lsf"), ("All Files", "*.*")],
        )
        if not file_path:
            return

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(lsf_text)

        self.status_lbl.config(text=f"Saved Lumerical script to: {file_path}")
        messagebox.showinfo(
            "Lumerical Script Generated",
            f"Successfully generated Ansys Lumerical 3D geometry script:\n\n{file_path}",
        )


def main():
    root = tk.Tk()
    app = LumericalGeometryApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
