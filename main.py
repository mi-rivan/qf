from qf import decoher

decoher.enable()

result = 10 / 0  # Fixed: removed unexpected indentation
print(result)

decoher.disable()
