# Program structure — pseudocode

Dependency direction: each module imports only from modules above it.
`config`, `design` and `geometry` import nothing from PsychoPy, so they can be
tested at a Python prompt with no window open.

    config      parameters only, no logic
    design      counterbalancing, formal contexts, trial sequencing
    geometry    ring positions, hit testing
    stimuli     manifest -> image objects
    response    responder objects (click / dwell / gaze-dwell)
    display     drawing routines
    trial       run one trial
    phases      training / practice / test runners
    session     assemble and run

---

## config.py

Parameters grouped by concern, so a change has one obvious home.

    DISPLAY  = {window_size, fullscreen, background, units}
    GEOMETRY = {ring_radius, n_positions, object_px, fixation_px,
                target_tolerance_px, fixation_tolerance_px}
    TIMING   = {preview_range, feedback_dur, iti, dwell_ms,
                fixation_hold_ms, fixation_timeout}
    CRITERION = {block_repeats, accuracy, consecutive_blocks, max_blocks}

    # What makes one phase differ from another. The trial code reads this
    # instead of branching on the phase name.
    PHASES = {
      "training":  {responder: "click",      feedback: True,  timeout: 10.0},
      "practice":  {responder: "dwell",      feedback: True,  timeout: 5.0},
      "test":      {responder: "dwell",      feedback: False, timeout: 2.0},
    }

    NAME_SETS = {"A": [...five CVCV...], "B": [...five CVCV...]}

---

## design.py   (no psychopy)

Everything about which condition a participant is in and what order things
happen. Pure functions of a subject id, so a given subject always gets the
same assignment.

    FORMAL_CONTEXTS = {"M3": {...}, "N5": {...}}

    function assign_cell(subject_id):
        # the 8-cell table: phase1 structure x continuity x stimulus/name set
        cell = CELLS[hash(subject_id) mod 8]
        return {phase1_structure, phase2_structure,
                phase1_set, phase2_set, phase1_names, phase2_names}

    function participant_ring_order(subject_id, objects):
        # fixed for this participant, random across participants
        return shuffle(objects, seed=subject_id)

    function training_block(objects, repeats):
        return shuffle(objects repeated `repeats` times)

    function test_sequence(objects, structure, n_trials):
        # Build consecutive pairs so that Direction conditions are balanced.
        # Direction is a property of (previous target -> current target),
        # so this returns a list where each element knows its predecessor.
        for each required Direction condition, in balanced proportion:
            pick a (prev, current) pair realising that condition
        return list of {target, prev_target, direction}

    function direction_of(prev, current, structure):
        # "upward" | "downward" | "unrelated", read off the lattice
        # For M3 this is a labelling convention, not a structural fact.

---

## geometry.py   (no psychopy)

    function ring_positions(radius, n, rotation_deg):
        # rotation drawn from 0..360/n; beyond that repeats
        return [(radius*cos(a), radius*sin(a)) for each a]

    function object_at(point, positions, names, tolerance):
        # returns the name whose position is within tolerance, else None
        # adjacent objects are 2*r*sin(pi/n) apart; tolerance must be
        # well under half of that so no point is inside two objects

---

## stimuli.py

    function load_set(window, stim_dir, set_name):
        manifest = read manifest.json
        return {object_name: ImageStim(file) for each object in that set}

---

## response.py

The abstraction that makes the tracker swap local. Three implementations,
one interface. The trial code never knows which one it holds.

    class Responder:
        start()      -> reset clock and internal state
        poll()       -> called once per frame; updates state
        result()     -> {selection, selection_ms, first_move_ms} or None

    class ClickResponder(Responder):
        poll: if button pressed and object_at(mouse) is not None -> select

    class DwellResponder(Responder):
        # pointer stands in for gaze
        poll: here = object_at(pointer)
              if here != dwelling_on: restart dwell clock
              elif dwell elapsed >= dwell_ms: select
              also record first time pointer left the centre

    class GazeDwellResponder(DwellResponder):
        # identical logic; the only change is where the sample comes from
        sample() -> tracker.get_latest_sample(), converted to centre-origin

Note that first_move_ms and selection are separate outputs. First movement is
the 5.1 latency measure; selection is the 5.3 error measure. Dwell selection
does not cost you the latency.

---

## display.py

Drawing only. No timing, no logic, no responses.

    function draw_fixation()
    function draw_array(stims, ring_order, positions)
    function draw_cue(name_text)
    function draw_feedback(correct_position, message)
    function show_message(text, keys) -> which key was pressed

---

## trial.py

One trial, for every phase. `phase_config` decides the differences.

    function run_trial(ctx, trial_spec, phase_config):

        positions = ring_positions(rotation = random 0..72)

        # 1. fixation, objects not yet shown
        #    TRACKER: wait for gaze within fixation tolerance, held for
        #    fixation_hold_ms, else timeout -> recycle trial
        acquire_fixation()

        # 2. preview: objects appear, fixation still required
        #    TRACKER: abort and recycle if fixation breaks
        draw_array(); draw_fixation(); flip()
        wait(random from preview_range)

        # 3. cue: the dot becomes the name, no gap
        draw_array(); draw_cue(); flip()
        mark_event("CUE_ONSET")

        responder.start()
        while elapsed < phase_config.timeout and responder.result() is None:
            responder.poll()
            redraw()
        outcome = responder.result()

        # 4. feedback, only if this phase has it
        if phase_config.feedback: draw_feedback(); wait(feedback_dur)

        # 5. blank interval — over which trial N's prime decays
        flip(); wait(iti)

        return log_row(trial_spec, outcome, positions, rotation)

---

## phases.py

Each runner builds a trial list, then executes it. Building and executing are
separate so the building can be tested alone.

    function run_training(ctx, names, phase_config):
        consecutive = 0; total = 0
        while consecutive < criterion.consecutive_blocks and blocks < max:
            specs = training_block(objects, repeats)
            rows  = [run_trial(...) for each spec]
            accuracy = mean(correct)
            consecutive = consecutive+1 if accuracy >= threshold else 0
            total += len(rows)
            show_message(block feedback)
        return total          # the 5.2 dependent measure

    function run_practice(ctx, names, phase_config):
        # self-terminated; count varies, so it is logged
        repeat:
            run one trial
        until participant chooses to continue

    function run_test(ctx, names, phase_config, structure):
        specs = test_sequence(objects, structure, n_trials)
        for each spec: run_trial(...)

---

## session.py

    function main(subject_id):
        cell = assign_cell(subject_id)
        ctx  = build context (window, stims, ring_order, logger, responder factory)

        show instructions
        n1 = run_training(phase1 set/names)
        run_practice(phase1 set/names)
        run_test(phase1 set/names, cell.phase1_structure)

        n2 = run_training(phase2 set/names)      # 5.2 measure lives here
        run_test(phase2 set/names, cell.phase2_structure)

        save_log()

---

## logging

One row per trial, written incrementally rather than at the end, so a crash
does not lose the session.

    columns: subject, cell, phase, block, trial_index,
             cue, target, prev_target, direction,
             response, correct, first_move_ms, selection_ms,
             rotation_deg, ring_order, timestamp

---

## What to test without a window

These are pure functions; call them at a Python prompt.

- `assign_cell` over many subject ids -> all 8 cells equally often
- `participant_ring_order` -> same id gives same order, different ids differ
- `ring_positions` -> five points, equal spacing, correct radius
- `object_at` -> no point falls inside two objects at the chosen tolerance
- `test_sequence` -> Direction conditions balanced, no illegal repeats
- `direction_of` -> agrees with the lattice for both M3 and N5
