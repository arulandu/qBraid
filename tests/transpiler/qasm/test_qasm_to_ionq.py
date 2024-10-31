# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Unit tests for qasm2/qasm3 to IonQDictType transpilation

"""
import importlib.util
from unittest.mock import Mock, patch

import openqasm3.ast
import pytest
from openqasm3.parser import parse

from qbraid.programs.gate_model.qasm3 import OpenQasm3Program
from qbraid.programs.typer import IonQDictType, Qasm3StringType
from qbraid.transpiler.conversions.openqasm3.openqasm3_to_ionq import (
    _parse_gates,
    extract_params,
    openqasm3_to_ionq,
)
from qbraid.transpiler.conversions.qasm2.qasm2_to_ionq import qasm2_to_ionq
from qbraid.transpiler.conversions.qasm3.qasm3_to_ionq import qasm3_to_ionq
from qbraid.transpiler.exceptions import CircuitConversionError


def test_ionq_device_extract_gate_data():
    """Test extracting gate data from a OpenQASM 2 program."""
    qasm = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[2];
    x q[0];
    not q[1];
    y q[0];
    z q[0], q[1];
    rx(pi / 4) q[0];
    ry(pi / 2) q[0];
    rz(3 * pi / 4) q[0];
    h q[0];
    h q;
    cx q[0], q[1];
    CX q[1], q[2];
    cnot q[2], q[0];
    ccx q[0], q[1], q[2];
    toffoli q[2], q[1], q[0];
    s q[0];
    sdg q[0];
    si q[0];
    t q[0];
    tdg q[0];
    ti q[1];
    sx q[0];
    v q[1];
    sxdg q[0];
    vi q[1];
    swap q[0], q[1];
    """

    gate_data = [
        {"gate": "x", "target": 0},
        {"gate": "not", "target": 1},
        {"gate": "y", "target": 0},
        {"gate": "z", "target": 0},
        {"gate": "z", "target": 1},
        {"gate": "rx", "target": 0, "rotation": 0.7853981633974483},
        {"gate": "ry", "target": 0, "rotation": 1.5707963267948966},
        {"gate": "rz", "target": 0, "rotation": 2.356194490192345},
        {"gate": "h", "target": 0},
        {"gate": "h", "target": 0},
        {"gate": "h", "target": 1},
        {"gate": "cnot", "control": 0, "target": 1},
        {"gate": "cnot", "control": 1, "target": 2},
        {"gate": "cnot", "control": 2, "target": 0},
        {"gate": "cnot", "controls": [0, 1], "target": 2},
        {"gate": "cnot", "controls": [2, 1], "target": 0},
        {"gate": "s", "target": 0},
        {"gate": "si", "target": 0},
        {"gate": "si", "target": 0},
        {"gate": "t", "target": 0},
        {"gate": "ti", "target": 0},
        {"gate": "ti", "target": 1},
        {"gate": "v", "target": 0},
        {"gate": "v", "target": 1},
        {"gate": "vi", "target": 0},
        {"gate": "vi", "target": 1},
        {"gate": "swap", "targets": [0, 1]},
    ]
    expected = {"qubits": 2, "circuit": gate_data, "gateset": "qis"}

    actual = qasm2_to_ionq(qasm)

    assert actual == expected


def test_qasm2_to_ionq_measurements_raises():
    """Test that qasm2_to_ionq raises an error when the circuit contains measurements."""
    qasm = """
    OPENQASM 2.0;
    include "qelib1.inc";
    qreg q[1];
    creg c[1];
    x q[0];
    measure q[0] -> c[0];
    """
    with pytest.raises(ValueError) as exc_info:
        qasm2_to_ionq(qasm)
    assert "Circuits with measurements are not supported by the IonQDictType" in str(exc_info.value)


@pytest.fixture
def deutsch_jozsa_qasm3() -> Qasm3StringType:
    """Return a QASM 3.0 string for the DJ algorithm."""
    return """
    OPENQASM 3.0;
    include "stdgates.inc";

    gate hgate q { h q; }
    gate xgate q { x q; }

    const int[32] N = 4;
    qubit[4] q;
    qubit ancilla;

    def deutsch_jozsa(qubit[N] q_func, qubit[1] ancilla_q) {
    xgate ancilla_q;
    for int i in [0:N-1] { hgate q_func[i]; }
    hgate ancilla_q;
    for int i in [0:N-1] { cx q_func[i], ancilla_q; }
    for int i in [0:N-1] { hgate q_func[i]; }
    }

    deutsch_jozsa(q, ancilla);
    """


@pytest.fixture
def deutch_jozsa_qasm3_unrolled() -> Qasm3StringType:
    """Return an unrolled QASM 3.0 string for the DJ algorithm."""
    return """
    OPENQASM 3.0;
    include "stdgates.inc";
    qubit[4] q;
    qubit[1] ancilla;
    x ancilla[0];
    h q[0];
    h q[1];
    h q[2];
    h q[3];
    h ancilla[0];
    cx q[0], ancilla[0];
    cx q[1], ancilla[0];
    cx q[2], ancilla[0];
    cx q[3], ancilla[0];
    h q[0];
    h q[1];
    h q[2];
    h q[3];
    """


@pytest.fixture
def deutch_jozsa_ionq() -> IonQDictType:
    """Return the expected IonQDictType for the DJ algorithm."""
    return {
        "qubits": 5,
        "circuit": [
            {"gate": "x", "target": 0},
            {"gate": "h", "target": 0},
            {"gate": "h", "target": 1},
            {"gate": "h", "target": 2},
            {"gate": "h", "target": 3},
            {"gate": "h", "target": 0},
            {"gate": "cnot", "control": 0, "target": 0},
            {"gate": "cnot", "control": 1, "target": 0},
            {"gate": "cnot", "control": 2, "target": 0},
            {"gate": "cnot", "control": 3, "target": 0},
            {"gate": "h", "target": 0},
            {"gate": "h", "target": 1},
            {"gate": "h", "target": 2},
            {"gate": "h", "target": 3},
        ],
        "gateset": "qis",
    }


@pytest.fixture
def ionq_native_gates_qasm() -> Qasm3StringType:
    """Return a QASM 3.0 using only IonQ native gates."""
    return """
    OPENQASM 3.0;
    qubit[3] q;
    ms(0,0) q[0], q[1];
    ms(-0.5,0.6,0.1) q[1], q[2];
    gpi(0) q[0];
    gpi2(0.2) q[1];
    """


@pytest.fixture
def ionq_native_gates_dict() -> IonQDictType:
    """Return an IonQDictType for a program using native gates."""
    return {
        "gateset": "native",
        "qubits": 3,
        "circuit": [
            {"gate": "ms", "targets": [0, 1], "phases": [0, 0]},
            {"gate": "ms", "targets": [1, 2], "phases": [-0.5, 0.6], "angle": 0.1},
            {"gate": "gpi", "phase": 0, "target": 0},
            {"gate": "gpi2", "phase": 0.2, "target": 1},
        ],
    }


def test_qasm3_to_ionq_no_pyqasm(deutsch_jozsa_qasm3):
    """Test transpiling the Deutsch-Jozsa algorithm from QASM 3.0 to IonQDictType."""
    with patch.dict("sys.modules", {"pyqasm": None}):
        with pytest.raises(CircuitConversionError) as exc_info:
            qasm3_to_ionq(deutsch_jozsa_qasm3)
        assert (
            "Failed to parse gate data from OpenQASM string. "
            "Please install the 'ionq' extra to enable program unrolling with pyqasm."
        ) in str(exc_info.value)


def test_qasm3_to_ionq_deutch_jozsa(
    deutsch_jozsa_qasm3, deutch_jozsa_qasm3_unrolled, deutch_jozsa_ionq
):
    """Test transpiling the Deutsch-Jozsa algorithm from QASM 3.0 to IonQDictType."""
    pyqasm_installed = importlib.util.find_spec("pyqasm") is not None
    qasm_program = deutsch_jozsa_qasm3 if pyqasm_installed else deutch_jozsa_qasm3_unrolled
    ionq_program = qasm3_to_ionq(qasm_program)
    assert ionq_program == deutch_jozsa_ionq


def test_qasm3_to_ionq_deutch_jozsa_pyqasm_mocked(
    deutsch_jozsa_qasm3, deutch_jozsa_qasm3_unrolled, deutch_jozsa_ionq
):
    """Test Deutch-Jozsa conversion with mock pyqasm import and unroll."""
    mock_pyqasm = Mock()
    mock_pyqasm.unroll.return_value = deutch_jozsa_qasm3_unrolled

    with patch.dict("sys.modules", {"pyqasm": mock_pyqasm}):
        qasm_program = deutsch_jozsa_qasm3
        ionq_program = qasm3_to_ionq(qasm_program)
        assert ionq_program == deutch_jozsa_ionq


def test_qasm3_to_ionq_native_gates(ionq_native_gates_qasm, ionq_native_gates_dict):
    """Test transpiling a program using IonQ native gates to IonQDictType."""
    ionq_program = qasm3_to_ionq(ionq_native_gates_qasm)
    assert ionq_program["qubits"] == ionq_native_gates_dict["qubits"]
    assert ionq_program["gateset"] == ionq_native_gates_dict["gateset"]
    assert ionq_program["circuit"] == ionq_native_gates_dict["circuit"]
    assert len(ionq_program) == 3


def test_qasm3_to_ionq_zz_native_gate():
    """Test transpiling a program containing the 'zz' native gate to IonQDictType."""
    qasm_program = """
    OPENQASM 3.0;
    qubit[2] q;
    zz(0.12) q[0], q[1];
    """
    expectd_ionq = {
        "gateset": "native",
        "qubits": 2,
        "circuit": [
            {"gate": "zz", "targets": [0, 1], "angle": 0.12},
        ],
    }

    assert qasm3_to_ionq(qasm_program) == expectd_ionq


@pytest.mark.parametrize(
    "qasm_code, error_message",
    [
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    ms(1.1,0) q[0], q[1];
    """,
            "Invalid phase value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    ms(0,-1.5) q[0], q[1];
    """,
            "Invalid phase value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    gpi(-6) q[0], q[1];
    """,
            "Invalid phase value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    gpi2(3.0) q[0], q[1];
    """,
            "Invalid phase value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    ms(0,0,0.26) q[0], q[1];
    """,
            "Invalid angle value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    ms(0,0,-0.1) q[0], q[1];
    """,
            "Invalid angle value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    zz(0.45) q[0], q[1];
    """,
            "Invalid angle value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    zz(-0.9) q[0], q[1];
    """,
            "Invalid angle value",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    zz(abc) q[0], q[1];
    """,
            "Invalid angle value",
        ),
    ],
)
def test_qasm3_to_ionq_invalid_params(qasm_code, error_message):
    """Test that qasm3_to_ionq raises an error when the circuit contains invalid parameters."""
    with pytest.raises(CircuitConversionError) as exc_info:
        qasm3_to_ionq(qasm_code)
    assert error_message in str(exc_info.value)


@pytest.mark.parametrize(
    "qasm_code, error_message",
    [
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    gpi q[0];
    """,
            "Phase parameter is required",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[1] q;
    rz q[0];
    """,
            "Angle parameter is required",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[2] q;
    zz q[0], q[1];
    """,
            "Angle parameter is required",
        ),
        (
            """
    OPENQASM 3.0;
    qubit[1] q;
    invalid_gate q[0];
    """,
            "Gate 'invalid_gate' not supported",
        ),
    ],
)
def test_openqasm3_to_ionq_value_errors(qasm_code, error_message):
    """Test that openqasm3_to_ionq raises an error when the circuit contains
    a gate that is missing required parameters or is not supported."""
    with pytest.raises(ValueError) as exc_info:
        openqasm3_to_ionq(qasm_code)
    assert error_message in str(exc_info.value)


def test_qasm3_to_ionq_mixed_gate_types_raises_value_error():
    """Test that qasm3_to_ionq raises an error when the circuit contains mixed gate types."""
    mixed_gate_qasm = """
    OPENQASM 3.0;
    qubit[2] q;
    h q[1];
    h q[2];
    gpi(0) q[0], q[1];
    """
    with pytest.raises(CircuitConversionError) as exc_info:
        qasm3_to_ionq(mixed_gate_qasm)
    assert "Cannot mix native and QIS gates in the same circuit." in str(exc_info.value)


def test_extract_params_index_error_caught():
    """Test that the extract_params returns empty list for non-parametric gates."""
    h_gate_qasm = """
    OPENQASM 3.0;
    qubit[1] q;
    h q[0];    
    """
    program = parse(h_gate_qasm)
    statement = program.statements[1]
    assert isinstance(statement, openqasm3.ast.QuantumGate)
    assert extract_params(statement) == []


@pytest.mark.parametrize(
    "program_text",
    [
        """
    OPENQASM 3.0;
    qubit[2] q;
    ms(0,0,0,0) q[0], q[1];
    """,
        """
    OPENQASM 3.0;
    qubit[2] q;
    ms q[0], q[1];
    """,
    ],
)
def test_ionq_ms_gate_wrong_number_params(program_text):
    """Test ValueError is raised when 'ms' gate has an invalid number of parameters."""
    program = OpenQasm3Program(program_text)

    with pytest.raises(ValueError) as exc_info:
        _ = _parse_gates(program)
    assert "Invalid number of parameters" in str(exc_info.value)