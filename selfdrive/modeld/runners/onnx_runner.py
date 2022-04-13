#!/usr/bin/env python3

import os
import sys
import numpy as np
import time

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"

import onnxruntime as ort # pylint: disable=import-error

def read(sz):
  dd = []
  gt = 0
  while gt < sz * 4:
    st = os.read(0, sz * 4 - gt)
    assert(len(st) > 0)
    dd.append(st)
    gt += len(st)
  return np.frombuffer(b''.join(dd), dtype=np.float32)

def write(d):
  os.write(1, d.tobytes())

def run_loop(m):
  ishapes = [[1]+ii.shape[1:] for ii in m.get_inputs()]
  keys = [x.name for x in m.get_inputs()]
  # onnxruntime-gpu needs time to initialize on first prediction
  print(m.get_providers(), file=sys.stderr)
  if "CUDAExecutionProvider" in m.get_providers():
    print('RUNNING PRE-INFERENCE', file=sys.stderr)
    t = time.time()
    m.run(None, dict(zip(keys, [np.zeros(shp, dtype=np.float32) for shp in ishapes])))
    print(time.time() - t, file=sys.stderr)
    t = time.time()
    m.run(None, dict(zip(keys, [np.zeros(shp, dtype=np.float32) for shp in ishapes])))
    print(time.time() - t, file=sys.stderr)
    time.sleep(2)
    t = time.time()
    m.run(None, dict(zip(keys, [np.zeros(shp, dtype=np.float32) for shp in ishapes])))
    print(time.time() - t, file=sys.stderr)
    t = time.time()
    m.run(None, dict(zip(keys, [np.zeros(shp, dtype=np.float32) for shp in ishapes])))
    print(time.time() - t, file=sys.stderr)
  print("ready to run onnx model", keys, ishapes, file=sys.stderr)
  while 1:
    t = time.time()
    inputs = []
    print(ishapes)
    for shp in ishapes:
      ts = np.product(shp)
      #print("reshaping %s with offset %d" % (str(shp), offset), file=sys.stderr)
      inputs.append(read(ts).reshape(shp))
    print('onnx_runner.py: {} s'.format(time.time() - t), file=sys.stderr)
    ret = m.run(None, dict(zip(keys, inputs)))
    print('onnx_runner.py: {} s'.format(time.time() - t), file=sys.stderr)
    #print(ret, file=sys.stderr)
    for r in ret:
      write(r)
    print('onnx_runner.py: {} s'.format(time.time() - t), file=sys.stderr)


if __name__ == "__main__":
  print("Onnx available providers: ", ort.get_available_providers(), file=sys.stderr)
  options = ort.SessionOptions()
  options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
  options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
  if 'OpenVINOExecutionProvider' in ort.get_available_providers() and 'ONNXCPU' not in os.environ:
    provider = 'OpenVINOExecutionProvider'
  elif 'CUDAExecutionProvider' in ort.get_available_providers() and 'ONNXCPU' not in os.environ:
    options.intra_op_num_threads = 2
    provider = 'CUDAExecutionProvider'
  else:
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 8
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    provider = 'CPUExecutionProvider'

  print("Onnx selected provider: ", [provider], file=sys.stderr)
  ort_session = ort.InferenceSession(sys.argv[1], options, providers=[provider])
  print("Onnx using ", ort_session.get_providers(), file=sys.stderr)
  run_loop(ort_session)
