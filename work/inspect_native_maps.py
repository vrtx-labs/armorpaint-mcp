import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

folder=Path(sys.argv[1])
with np.load(folder/'mesh_maps.npz') as data:
    valid=data['coverage']>.5
    result={}
    for key in data.files:
        if key=='coverage':
            continue
        values=data[key][valid]
        result[key]={'shape':list(data[key].shape),'min':float(values.min()),'max':float(values.max()),
                     'mean':np.mean(values,axis=0).tolist(),'std':np.std(values,axis=0).tolist()}
    print(json.dumps(result,indent=2))
    (folder/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
