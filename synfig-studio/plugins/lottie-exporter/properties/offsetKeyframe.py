"""
Will store all the function necessary for generation of offset properties of a
keyframe in lottie
"""
import sys
import copy
import settings
from misc import parse_position, change_axis, Vector
sys.path.append("..")

def isclose(a_val, b_val, rel_tol=1e-09, abs_tol=0.0):
    """
    A Function for testing approximate equality
    """
    return abs(a_val - b_val) <= max(rel_tol * max(abs(a_val), abs(b_val)), abs_tol)

def clamped_tangent(p1, p2, p3, animated, i):
    """
    Function corresponding to clamped function in Synfig
    It generates the tangent when clamped waypoints are used
    """
    # pw -> prev_waypoint, w -> waypoint, nw -> next_waypoint
    pw, w, nw = animated[i-1], animated[i], animated[i+1]
    t1 = float(pw.attrib["time"][:-1]) * settings.lottie_format["fr"]
    t2 = float(w.attrib["time"][:-1]) * settings.lottie_format["fr"]
    t3 = float(nw.attrib["time"][:-1]) * settings.lottie_format["fr"]
    bias = 0.0
    tangent = 0.0
    pm = p1 + (p3 - p1)*(t2 - t1)/(t3 - t1)
    if p3 > p1:
        if p2 >= p3 or p2 <= p1:
            tangent = tangent * 0.0
        else:
            if p2 > pm:
                bias = (pm - p2) / (p3 - pm)
            elif p2 < pm:
                bias = (pm - p2) / (pm - p1)
            else:
                bias = 0.0
            tangent = (p2 - p1) * (1.0 + bias) / 2.0 + (p3 - p2) * (1.0 - bias) / 2.0
    elif p1 > p2:
        if p2 >= p1 or p2 <= p3:
            tangent = tangent * 0.0
        else:
            if p2 > pm:
                bias = (pm - p2) / (pm - p1)
            elif p2 < pm:
                bias = (pm - p2) / (p3 - pm)
            else:
                bias = 0.0
            tangent = (p2 - p1) * (1.0 + bias) / 2.0 + (p3 - p2) * (1.0 - bias) / 2.0
    else:
        tangent = tangent * 0.0
    return tangent

def clamped_vector(p1, p2, p3, animated, i, lottie, ease):
    """
    Function to generate the collective tangents i.e. x tangent and y tangent
    when clamped waypoints are used
    """
    x_tan = clamped_tangent(p1.val1, p2.val1, p3.val1, animated, i)
    y_tan = clamped_tangent(p1.val2, p2.val2, p3.val2, animated, i)
    if isclose(x_tan, 0.0) or isclose(y_tan, 0.0):
        if ease == "in":
            ease_in(lottie)
        else:
            ease_out(lottie)
    return Vector(x_tan, y_tan, animated.attrib["type"])

def ease_out(lottie):
    """
    To set the ease out values in lottie format
    """
    lottie["o"]["x"] = settings.OUT_TANGENT_X
    lottie["o"]["y"] = settings.OUT_TANGENT_Y

def ease_in(lottie):
    """
    To set the ease in values in lottie format
    """
    lottie["i"]["x"] = settings.IN_TANGENT_X
    lottie["i"]["y"] = settings.IN_TANGENT_Y

def handle_color():
    """
    Default linear tangent values for color interpolations
    """
    out_val = Vector(0.5, 0.5, "color")
    in_val = Vector(0.5, 0.5, "color")
    return out_val, in_val

def calc_tangent(animated, lottie, i):
    """
    Calculates the tangent, given two waypoints and there interpolation methods
    """
    waypoint, next_waypoint = animated[i], animated[i+1]
    cur_get_after, next_get_before = waypoint.attrib["after"], next_waypoint.attrib["before"]
    cur_get_before, next_get_after = waypoint.attrib["before"], next_waypoint.attrib["after"]

    if animated.attrib["type"] == "angle":
        if cur_get_after == "auto":
            cur_get_after = "linear"
        if cur_get_before == "auto":
            cur_get_before = "linear"
        if next_get_before == "auto":
            next_get_before = "linear"
        if next_get_after == "auto":
            next_get_after = "linear"

    # Synfig only supports constant interpolations for points
    if animated.attrib["type"] == "points":
        cur_get_after = "constant"
        cur_get_before = "constant"
        next_get_after = "constant"
        next_get_before = "constant"

    # After effects only supports linear,ease-in,ease-out and constant interpolations for color
    ##### No support for TCB and clamped interpolations in color is there yet #####
    if animated.attrib["type"] == "color":
        if cur_get_after in {"auto", "clamped"}:
            cur_get_after = "linear"
        if cur_get_before in {"auto", "clamped"}:
            cur_get_before = "linear"
        if next_get_before in {"auto", "clamped"}:
            next_get_before = "linear"
        if next_get_after in {"auto", "clamped"}:
            next_get_after = "linear"

    # Calculate positions of waypoints
    cur_pos = parse_position(animated, i)
    prev_pos = copy.deepcopy(cur_pos)
    next_pos = parse_position(animated, i + 1)
    after_next_pos = copy.deepcopy(next_pos)

    if i + 2 <= len(animated) - 1:
        after_next_pos = parse_position(animated, i + 2)
    if i - 1 >= 0:
        prev_pos = parse_position(animated, i - 1)

    tens, bias, cont = 0, 0, 0   # default values
    tens1, bias1, cont1 = 0, 0, 0
    if "tension" in waypoint.keys():
        tens = float(waypoint.attrib["tension"])
    if "continuity" in waypoint.keys():
        cont = float(waypoint.attrib["continuity"])
    if "bias" in waypoint.keys():
        bias = float(waypoint.attrib["bias"])
    if "tension" in next_waypoint.keys():
        tens1 = float(next_waypoint.attrib["tension"])
    if "continuity" in next_waypoint.keys():
        cont1 = float(next_waypoint.attrib["continuity"])
    if "bias" in next_waypoint.keys():
        bias1 = float(next_waypoint.attrib["bias"])


    ### Special case for color interpolations ###
    if animated.attrib["type"] == "color":
        if cur_get_after == "linear" and next_get_before == "linear":
            return handle_color()

    # iter           next
    # ANY/TCB ------ ANY/ANY
    if cur_get_after == "auto":
        if i >= 1:
            out_val = ((1 - tens) * (1 + bias) * (1 + cont) *\
                       (cur_pos - prev_pos))/2 +\
                       ((1 - tens) * (1 - bias) * (1 - cont) *\
                       (next_pos - cur_pos))/2
        else:
            out_val = next_pos - cur_pos      # t1 = p2 - p1

    # iter           next
    # ANY/LINEAR --- ANY/ANY
    # ANY/EASE   --- ANY/ANY
    if cur_get_after in {"linear", "halt"}:
        out_val = next_pos - cur_pos

    # iter          next
    # ANY/ANY ----- LINEAR/ANY
    # ANY/ANY ----- EASE/ANY
    if next_get_before in {"linear", "halt"}:
        in_val = next_pos - cur_pos

    # iter          next
    # ANY/CLAMPED - ANY/ANY
    if cur_get_after == "clamped":
        if i >= 1:
            ease = "out"
            out_val = clamped_vector(prev_pos, cur_pos, next_pos, animated, i, lottie, ease)
        else:
            out_val = next_pos - cur_pos      # t1 = p2 - p1

    # iter          next             after_next
    # ANY/ANY ----- CLAMPED/ANY ---- ANY/ANY
    if next_get_before == "clamped":
        if i + 2 <= len(animated) - 1:
            ease = "in"
            in_val = clamped_vector(cur_pos,
                                    next_pos,
                                    after_next_pos,
                                    animated,
                                    i + 1,
                                    lottie,
                                    ease)
        else:
            in_val = next_pos - cur_pos     # t2 = p2 - p1

    # iter              next
    # ANY/CONSTANT ---- ANY/ANY
    # ANY/ANY      ---- CONSTANT/ANY
    if cur_get_after == "constant" or next_get_before == "constant":
        lottie["h"] = 1
        if animated.attrib["type"] == "vector":
            del lottie["to"], lottie["ti"]
        del lottie["i"], lottie["o"]
        # "e" is not needed, but is still not deleted as
        # it is of use in the last iteration of animation
        # See properties/multiDimenstionalKeyframed.py for more details
        # del lottie["e"]

        # If the number of points is decresing, then hold interpolation should
        # have reverse effect. The value should instantly decrease and remain
        # same for the rest of the interval
        if animated.attrib["type"] == "points":
            if i > 0 and prev_pos.val1 > cur_pos.val1:
                t_now = float(animated[i-1].attrib["time"][:-1]) * settings.lottie_format["fr"] + 1
                lottie["t"] = t_now
        return

    # iter           next           after_next
    # ANY/ANY ------ TCB/ANY ------ ANY/ANY
    if next_get_before == "auto":
        if i + 2 <= len(animated) - 1:
            in_val = ((1 - tens1) * (1 + bias1) * (1 - cont1) *\
                      (next_pos - cur_pos))/2 +\
                      ((1 - tens1) * (1 - bias1) * (1 + cont1) *\
                      (after_next_pos - next_pos))/2
        else:
            in_val = next_pos - cur_pos      # t2 = p2 - p1
    return out_val, in_val

def gen_properties_offset_keyframe(curve_list, animated, i):
    """
     Generates the dictionary corresponding to properties/offsetKeyFrame.json
    """
    lottie = curve_list[-1]

    waypoint, next_waypoint = animated[i], animated[i+1]
    cur_get_after, next_get_before = waypoint.attrib["after"], next_waypoint.attrib["before"]
    cur_get_before, next_get_after = waypoint.attrib["before"], next_waypoint.attrib["after"]

    # "angle" interpolations never call this function, can be removed by confirming
    if animated.attrib["type"] == "angle":
        if cur_get_after == "auto":
            cur_get_after = "linear"
        if cur_get_before == "auto":
            cur_get_before = "linear"
        if next_get_before == "auto":
            next_get_before = "linear"
        if next_get_after == "auto":
            next_get_after = "linear"

    # Synfig only supports constant interpolations for points
    # "points" never call this function, can be removed by confirming
    if animated.attrib["type"] == "points":
        cur_get_after = "constant"
        cur_get_before = "constant"
        next_get_after = "constant"
        next_get_before = "constant"

    # Calculate positions of waypoints
    cur_pos = parse_position(animated, i)
    next_pos = parse_position(animated, i + 1)

    lottie["i"] = {}    # Time bezier curve, not used in synfig
    lottie["o"] = {}    # Time bezier curve, not used in synfig
    lottie["i"]["x"] = 0.5
    lottie["i"]["y"] = 0.5
    lottie["o"]["x"] = 0.5
    lottie["o"]["y"] = 0.5
    if cur_get_after == "halt": # For ease out
        ease_out(lottie)
    if next_get_before == "halt": # For ease in
        ease_in(lottie)
    lottie["t"] = float(waypoint.attrib["time"][:-1]) * settings.lottie_format["fr"]
    lottie["s"] = [cur_pos.val1, cur_pos.val2]
    lottie["e"] = [next_pos.val1, next_pos.val2]
    #lottie["s"] = change_axis(cur_pos.val1, cur_pos.val2)
    #lottie["e"] = change_axis(next_pos.val1, next_pos.val2)
    lottie["to"] = []
    lottie["ti"] = []

    # Calculating the unchanged tangent
    try:
        out_val, in_val = calc_tangent(animated, lottie, i)
    except Exception as excep:
        # This means constant interval
        return excep

    # This module is only needed for origin animation
    lottie["to"] = out_val.get_list()
    lottie["ti"] = in_val.get_list()

    # TCB/!TCB and list is not empty
    if cur_get_before == "auto" and cur_get_after != "auto" and i > 0:
        curve_list[-2]["ti"] = copy.deepcopy(lottie["to"])
        curve_list[-2]["ti"] = [-item/settings.TANGENT_FACTOR for item in curve_list[-2]["ti"]]
        curve_list[-2]["ti"][1] = -curve_list[-2]["ti"][1]
        if cur_get_after == "halt":
            curve_list[-2]["i"]["x"] = settings.IN_TANGENT_X
            curve_list[-2]["i"]["y"] = settings.IN_TANGENT_Y

    # Lottie and synfig use different tangents SEE DOCUMENTATION
    lottie["ti"] = [-item for item in lottie["ti"]]

    # Lottie tangent length is larger than synfig
    lottie["ti"] = [item/settings.TANGENT_FACTOR for item in lottie["ti"]]
    lottie["to"] = [item/settings.TANGENT_FACTOR for item in lottie["to"]]

    # IMPORTANT to and ti have to be relative
    # The y-axis is different in lottie
    lottie["ti"][1] = -lottie["ti"][1]
    lottie["to"][1] = -lottie["to"][1]
