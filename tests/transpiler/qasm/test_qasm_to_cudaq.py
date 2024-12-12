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
Unit tests for OpenQASM 3.0 to CUDA-Q kernel transpilation.

"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
from openqasm3.parser import parse
from qiskit.circuit.random import random_clifford_circuit
from qiskit.qasm3 import dumps as qasm3_dumps
from qiskit.qasm3 import loads as qasm3_loads
from qiskit_aer import StatevectorSimulator

from qbraid.interface import circuits_allclose, assert_allclose_up_to_global_phase
from qbraid.transpiler.conversions.openqasm3 import openqasm3_to_cudaq
from qbraid.transpiler.conversions.qasm2.qasm2_to_qasm3 import qasm2_to_qasm3

cudaq = pytest.importorskip("cudaq")

if TYPE_CHECKING:
    from cudaq import PyKernel
    from qiskit import QuantumCircuit


def _check_output(qasm3_str_in: str, cudaq_out: PyKernel, atol=1e-7, method="circ"):
    """Check output given the input OpenQASM 3.0 program and the CUDA-Q kernel.
    Args
        qasm3_str_in (str): OpenQASM 3.0 input program
        cudaq_out (PyKernel): CUDA-Q kernel equivalent to input string
        method (str):
        - 'circ' to use CUDA-Q translate -> OpenQASM 2 -> Qiskit circuits -> all close.
        - 'state' to compute statevectors -> all close. requires no measurement.
    """
    if method == "circ":
        qasm2_str_out = cudaq.translate(cudaq_out, format="openqasm2")
        qasm3_str_out = qasm2_to_qasm3(qasm2_str_out)
        circ_in, circ_out = qasm3_loads(qasm3_str_in), qasm3_loads(qasm3_str_out)

        assert circuits_allclose(circ_in, circ_out, atol=atol)
    elif method == "state":
        circ_in: QuantumCircuit = qasm3_loads(qasm3_str_in)
        state_out = np.array(cudaq.get_state(cudaq_out))

        sim = StatevectorSimulator()
        job = sim.run(circ_in, shots=1)
        res = job.result().results[0]
        state_in = res.data.statevector.data

        assert_allclose_up_to_global_phase(state_in, state_out, atol=atol)


def test_openqasm3_to_cudaq():
    """Test converting an OpenQASM3 program to a CUDA-Q kernel."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[1] q;
    bit[1] b;

    h q[0];
    x q[0];
    y q[0];
    z q[0];
    t q[0];
    s q[0];

    b[0] = measure q[0];
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_identifiers():
    """OpenQASM3 -> CUDA-Q: Test gate operations and assignments with identifiers and indexing."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[3] q;
    bit[3] b;

    h q;
    x q[1];

    b = measure q;
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_rotation_gates():
    """OpenQASM3 -> CUDA-Q: Test a RX gate with a float literal argument."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    bit[2] b;

    rx(5.25) q[0];

    b = measure q;
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_two_qubit_gates():
    """OpenQASM3 -> CUDA-Q: Test a SWAP gate."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    bit[2] b;

    swap q[0], q[1];

    b = measure q;
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


@pytest.mark.skip(reason="pyqasm don't support ctrl modifiers")
def test_openqasm3_to_cudaq_ctrl_modifier():
    """OpenQASM3 -> CUDA-Q: Test a ctrl modifier on an x gate."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    bit[2] b;
    ctrl @ x q[0], q[1];

    b = measure q;
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out, method="state")


def test_openqasm3_to_cudaq_controlled_gates():
    """OpenQASM3 -> CUDA-Q: Test a controlled x gate."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[2] q;
    cx q[0], q[1];
    """
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out, method="state")


def test_openqasm3_to_cudaq_adj_gates():
    """OpenQASM3 -> CUDA-Q: Test adjoint modifier with sdg/tdg gates."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit q;
    tdg q;
    sdg q;
    """

    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_inv_modifier():
    """OpenQASM3 -> CUDA-Q: Test inv modifier"""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[1] q;
    inv @ x q[0];
    """

    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_pow_modifier():
    """OpenQASM3 -> CUDA-Q: Test pow modifier"""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[1] q;
    pow(4) @ x q[0];
    """

    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out)


def test_openqasm3_to_cudaq_arith():
    """OpenQASM3 -> CUDA-Q: Test arithmetic expression evaluation"""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    qubit[1] q;
    ry(3*pi/4) q[0];
    """

    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out, atol=1e-6)  # TODO: fails for 1e-7 due to rounding


def test_openqasm3_to_cudaq_custom_gates():
    """OpenQASM3 -> CUDA-Q: Test custom parameterized and non-parameterized gates."""

    qasm3_str_in = """
    OPENQASM 3.0;
    include "stdgates.inc";

    gate aca q {
        h q;
        x q;
    }
    
    gate acap(t) q {
        rx(t) q;
        y q;
        rz(5*t) q;
    }

    qubit[1] q;
    aca q[0];
    acap(pi/25) q[0];
    """

    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out, atol=1e-6)


@pytest.mark.parametrize("num_qubits", [2, 3, 4, 5])
@pytest.mark.parametrize("_", range(10))
def test_openqasm3_to_cudaq_random_clifford_circuit(num_qubits, _):
    """OpenQASM 3.0 -> CUDA-Q: Test a random circuit"""

    num_gates = np.random.randint(1, 11)
    all_gates = {
        "i",
        "x",
        "y",
        "z",
        "h",
        "s",
        "sdg",
        "sx",
        "sxdg",
        "cx",
        "cz",
        "cy",
        "swap",
        "iswap",
        "ecr",
        "dcx",
    }

    circ = random_clifford_circuit(
        num_qubits, num_gates, gates=list(all_gates - {"sx", "sxdg", "ecr", "dcx", "iswap"})
    )
    qasm3_str_in = qasm3_dumps(circ)
    qasm3_in = parse(qasm3_str_in)

    cudaq_out = openqasm3_to_cudaq(qasm3_in)

    _check_output(qasm3_str_in, cudaq_out, method="state")
