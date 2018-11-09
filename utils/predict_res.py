def local_test():
    from keras.models import model_from_json
    import numpy as np

    json_file = open("../model/model.json", "r") 
    loaded_model_json = json_file.read() 
    json_file.close() 

    model = model_from_json(loaded_model_json)
    model.load_weights('../model/resnet.hdf5')

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

def remote_control(target_ip, redis_address):
    from keras.models import model_from_json
    import numpy as np
    import redis

    json_file = open("../model/model.json", "r") 
    loaded_model_json = json_file.read() 
    json_file.close() 

    model = model_from_json(loaded_model_json)
    model.load_weights('../model/resnet.hdf5')

    r = redis.StrictRedis(host=redis_address, port=6379, db=1)

    def parse_message(self,message):
        # Parse message from data_sender.py via redis
        message = message.decode("utf-8")
        message = message.replace('<','\'<')
        message = message.replace('>','>\'')

        msg = eval(message)
        ob = msg['game_data']
        s = msg['image_data']

        # Decode image within base64 
        s = base64.b64decode(s)
        s = Image.open(BytesIO(s))

        # s = s.resize((576,160), Image.ANTIALIAS)
        s = np.array(s)

        return ob, s

    while True:
        message = r.hget('pcars_data'+target_ip,target_ip)
        print(message)
        if message:
            # r.hdel('pcars_data'+target_ip,target_ip)

            data, image = parse_message(message)

            print(data)

if __name__ == "__main__":
    remote_control('165.132.108.169','redis.hwanmoo.kr')