/*
 * test_list.h - the test cases (X-macro) and their prototypes.
 * Test infrastructure.
 */
#ifndef PEN_TEST_LIST_H
#define PEN_TEST_LIST_H

#define TEST_LIST(X)                          \
    X(test_crc_known_answer)                  \
    X(test_log_header_roundtrip)              \
    X(test_log_records_roundtrip)             \
    X(test_log_unit_conversion)               \
    X(test_log_corruption_detected)           \
    X(test_log_golden_file)                   \
    X(test_log_session_clock)                 \
    X(test_biquad_vs_scipy)                   \
    X(test_jacobian_vs_frames)                \
    X(test_jacobian_properties)               \
    X(test_limiter_radial_properties)         \
    X(test_limiter_slew_properties)           \
    X(test_authority_smoothing)               \
    X(test_kf_step_golden)                    \
    X(test_kf_estimator_sequence_golden)      \
    X(test_kf_float32_covariance_health)      \
    X(test_bpf_estimator_golden)              \
    X(test_replay_sim_kf)                     \
    X(test_replay_sim_bpf)                    \
    X(test_replay_sim_ffc)                    \
    X(test_replay_sim_kf_authority)           \
    X(test_bpf_reacquisition_transient)       \
    X(test_guided_tracks_template)            \
    X(test_current_loop_bridge_mapping)       \
    X(test_current_loop_step_response)        \
    X(test_current_loop_voltage_clamp)        \
    X(test_current_loop_offset_calibration)   \
    X(test_closed_loop_step_response)         \
    X(test_closed_loop_bandwidth)             \
    X(test_closed_loop_margins)               \
    X(test_closed_loop_hold_no_vsat)          \
    X(test_thermal_model_steady_state)        \
    X(test_thermal_resistance_estimate)       \
    X(test_thermal_ntc_and_derating)          \
    X(test_safety_hall_stuck)                 \
    X(test_safety_hall_residual_and_range)    \
    X(test_safety_headroom)                   \
    X(test_safety_optical)                    \
    X(test_safety_battery)                    \
    X(test_safety_overcurrent_latch_clear)    \
    X(test_safety_ml_trips)                   \
    X(test_sm_transition_table)               \
    X(test_sm_fault_policies)                 \
    X(test_ml_guard_rejects)                  \
    X(test_ml_guard_fallback_within_20ms)     \
    X(test_ml_window)                         \
    X(test_calib_record_roundtrip)            \
    X(test_calib_record_corruption)           \
    X(test_calib_spectral_f0)                 \
    X(test_calib_gate_rule)                   \
    X(test_hall_conversion)                   \
    X(test_fusion_matches_sim_scheme)         \
    X(test_attitude_from_gravity)             \
    X(test_system_hall_frozen_detect)         \
    X(test_system_fault_sequences)            \
    X(test_system_capture_boundaries)

#define TEST_DECL(name) void name(void);
TEST_LIST(TEST_DECL)
#undef TEST_DECL

/* golden log writer (tests/test_log.c), used by `pen_tests --golden-log` */
int pen_write_golden_log(const char *path);

#endif /* PEN_TEST_LIST_H */
