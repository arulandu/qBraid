"""
====================================
 Circuits (:mod:`qbraid.circuits`)
====================================

.. currentmodule:: qbraid.circuits

Overview
---------
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus viverra auctor euismod.
Nullam feugiat ante eget diam ultrices imperdiet. In bibendum lorem tincidunt tincidunt feugiat.
Phasellus ac nibh non massa tincidunt consectetur eget ultrices massa. Sed pulvinar gravida odio
quis posuere. Sed nibh leo, egestas vitae iaculis id, dignissim eget massa. Nullam bibendum cursus
elit a efficitur. Maecenas dignissim, justo id tincidunt feugiat, quam est bibendum velit, ultrices
sagittis nibh magna quis nunc. Fusce ullamcorper dictum nibh, sit amet molestie dolor semper vel.

Example Usage
--------------

    .. code-block:: python

        from qbraid.circuits import Circuit, H, CX, drawer

        h, cx = H(0), CX(1)                 # initialize each gate by assigning a global phase.
        circuit = Circuit(num_qubits=2)     # specify the number of qubits that will be used
        circuit.append([h(0), cx([0, 1])])  # assign qubits to each gate and append to circuit
        drawer(circuit)                     # print out the resulting circuit
        ...

Circuits API
-------------

.. autosummary::
   :toctree: ../stubs/

   Circuit
   Gate
   Instruction
   Qubit
   UpdateRule
   drawer
   CircuitError

"""
from .circuit import Circuit
from .gate import Gate
from .instruction import Instruction
from .qubit import Qubit
from .update_rule import UpdateRule
from .drawer import drawer
from .exceptions import CircuitError
