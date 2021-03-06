# Copyright 2020 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Utility functions for FlatBuffers.

All functions that are commonly used to work with FlatBuffers.

Refer to the tensorflow lite flatbuffer schema here:
tensorflow/lite/schema/schema.fbs

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import copy
import os
import random

from flatbuffers.python import flatbuffers
from tensorflow.lite.python import schema_py_generated as schema_fb

_TFLITE_FILE_IDENTIFIER = b'TFL3'


def convert_bytearray_to_object(model_bytearray):
  """Converts a tflite model from a bytearray to an object for parsing."""
  model_object = schema_fb.Model.GetRootAsModel(model_bytearray, 0)
  return schema_fb.ModelT.InitFromObj(model_object)


def read_model(input_tflite_file):
  """Reads a tflite model as a python object.

  Args:
    input_tflite_file: Full path name to the input tflite file

  Raises:
    RuntimeError: If input_tflite_file path is invalid.
    IOError: If input_tflite_file cannot be opened.

  Returns:
    A python object corresponding to the input tflite file.
  """
  if not os.path.exists(input_tflite_file):
    raise RuntimeError('Input file not found at %r\n' % input_tflite_file)
  with open(input_tflite_file, 'rb') as file_handle:
    model_bytearray = bytearray(file_handle.read())
  return convert_bytearray_to_object(model_bytearray)


def read_model_with_mutable_tensors(input_tflite_file):
  """Reads a tflite model as a python object with mutable tensors.

  Similar to read_model() with the addition that the returned object has
  mutable tensors (read_model() returns an object with immutable tensors).

  Args:
    input_tflite_file: Full path name to the input tflite file

  Raises:
    RuntimeError: If input_tflite_file path is invalid.
    IOError: If input_tflite_file cannot be opened.

  Returns:
    A mutable python object corresponding to the input tflite file.
  """
  return copy.deepcopy(read_model(input_tflite_file))


def convert_object_to_bytearray(model_object):
  """Converts a tflite model from an object to a bytearray."""
  # Initial size of the buffer, which will grow automatically if needed
  builder = flatbuffers.Builder(1024)
  model_offset = model_object.Pack(builder)
  builder.Finish(model_offset, file_identifier=_TFLITE_FILE_IDENTIFIER)
  model_bytearray = bytes(builder.Output())
  return model_bytearray


def write_model(model_object, output_tflite_file):
  """Writes the tflite model, a python object, into the output file.

  Args:
    model_object: A tflite model as a python object
    output_tflite_file: Full path name to the output tflite file.

  Raises:
    IOError: If output_tflite_file path is invalid or cannot be opened.
  """
  model_bytearray = convert_object_to_bytearray(model_object)
  with open(output_tflite_file, 'wb') as out_file:
    out_file.write(model_bytearray)


def strip_strings(model):
  """Strips all nonessential strings from the model to reduce model size.

  We remove the following strings:
  (find strings by searching ":string" in the tensorflow lite flatbuffer schema)
  1. Model description
  2. SubGraph name
  3. Tensor names
  We retain OperatorCode custom_code and Metadata name.

  Args:
    model: The model from which to remove nonessential strings.

  """

  model.description = ''
  for subgraph in model.subgraphs:
    subgraph.name = ''
    for tensor in subgraph.tensors:
      tensor.name = ''


def randomize_weights(model, random_seed=0):
  """Randomize weights in a model.

  Args:
    model: The model in which to randomize weights.
    random_seed: The input to the random number generator (default value is 0).

  """

  # The input to the random seed generator. The default value is 0.
  random.seed(random_seed)

  # Parse model buffers which store the model weights
  buffers = model.buffers
  for i in range(1, len(buffers)):  # ignore index 0 as it's always None
    buffer_i_data = buffers[i].data
    buffer_i_size = 0 if buffer_i_data is None else buffer_i_data.size

    # Raw data buffers are of type ubyte (or uint8) whose values lie in the
    # range [0, 255]. Those ubytes (or unint8s) are the underlying
    # representation of each datatype. For example, a bias tensor of type
    # int32 appears as a buffer 4 times it's length of type ubyte (or uint8).
    # TODO(b/152324470): This does not work for float as randomized weights may
    # end up as denormalized or NaN/Inf floating point numbers.
    for j in range(buffer_i_size):
      buffer_i_data[j] = random.randint(0, 255)
