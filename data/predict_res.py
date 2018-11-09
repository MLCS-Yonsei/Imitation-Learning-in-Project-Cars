from keras.models import model_from_json
import numpy as np

json_file = open("model.json", "r") 
loaded_model_json = json_file.read() 
json_file.close() 

model = model_from_json(loaded_model_json)
model.load_weights('resnet.hdf5')

x = np.load('./test.npz')

_imgs = x['image']
_data = x['data']

r = model.predict([_imgs,_data[:,7]])

import matplotlib.pyplot as plt

for i, _img in enumerate(_imgs):
    imgplot = plt.imshow(_img)
    _steer = r[0][i]
    _acc = r[1][i]
    _brake = r[2][i]

    print("step",i,"steer",int(_steer*100)/100,"acc",int(_acc*100)/100,"brake",int(_brake*100)/100)
    plt.show()