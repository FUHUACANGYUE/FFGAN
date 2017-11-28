#codingL utf-8
import os
import scipy
import numpy as np
import tensorflow as tf
from PIL import Image
import matplotlib.pyplot as plt
import struct

from config import cfg

class loadData(object):
    '''
    Load Data from image. 
    args:
        batch_size: size of every train batch
        train_shuffle: whether shuffle the train set
    '''
    def __init__(self, batch_size = 100, train_shuffle = True):
        
        self.batch_size = batch_size
        #self.train_list = np.loadtxt('setting1_train.txt', dtype='string',delimiter=',')
        self.train_list = np.loadtxt('session01_train_shuffle.txt', dtype='string',delimiter=',')
        self.train_index = 0
        if train_shuffle:
            np.random.shuffle(self.train_list)
        
        self.test_list = np.loadtxt('session01_test2.txt', dtype='string',delimiter=',')
        self.test_index = 0
        
        if cfg.crop:
            # centre-crop
            w_crop1, h_crop1 = (cfg.ori_width - cfg.width)/2, (cfg.ori_height - cfg.height)/2
            w_crop2, h_crop2 = cfg.ori_width - w_crop1, cfg.ori_height - h_crop1
            self.crop_box = (w_crop1, h_crop1, w_crop2, h_crop2)
        
        if not cfg.use_profile:
            self.f_train = open('session01_train_shuffle_feature', 'r')
            self.f_test = open('session01_test2_feature', 'r')
            
        assert Image.open(os.path.join(cfg.data_path, self.train_list[0,0])).size == \
                            (cfg.ori_width, cfg.ori_height)
        assert Image.open(os.path.join(cfg.data_path, self.test_list[0,0])).size == \
                            (cfg.ori_width, cfg.ori_height)
    
    def get_train_batch(self):
        '''
        get train images by batch
        return:
            train profile images and front images
        '''
        trX = np.zeros((self.batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        trY = np.zeros((self.batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        for i in range(self.batch_size):
            try:
                trX[i] = self.read_image(self.train_list[i + self.train_index][0])
                trY[i] = self.read_image(self.train_list[i + self.train_index][1])
            except:
                self.train_index = -i
                trX[i] = self.read_image(self.train_list[i +self.train_index][0])
                trY[i] = self.read_image(self.train_list[i +self.train_index][1])
        self.train_index += self.batch_size
        return(trX, trY)
    
    def get_train_batch_feature(self):
        '''
        get train images by batch
        return:
            train feature of profile images and front images
        '''
        trX = np.zeros((self.batch_size, 4096), dtype=np.float32)
        trY = np.zeros((self.batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        for i in range(self.batch_size):
            try:
                trX[i] = self.read_feature(self.f_train)
                trY[i] = self.read_image(self.train_list[i + self.train_index][1])
            except:
                self.train_index = -i
                self.f_train.seek(0)
                trX[i] = self.read_feature(self.f_train)
                trY[i] = self.read_image(self.train_list[i +self.train_index][1])
        self.train_index += self.batch_size
        return(trX, trY)
        
    def get_test_batch(self, batch_size = cfg.batch_size):
        '''
        get test images by batch
        args:
            batch size
        return:
            test profile images and front images
        '''
        teX = np.zeros((batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        teY = np.zeros((batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        for i in range(batch_size):
            try:
                teX[i] = self.read_image(self.test_list[i +self.test_index][0])
                teY[i] = self.read_image(self.test_list[i +self.test_index][1])
            except:
                self.test_index = -i
                teX[i] = self.read_image(self.test_list[i +self.test_index][0])
                teY[i] = self.read_image(self.test_list[i +self.test_index][1])
        self.test_index += batch_size
        return(teX, teY)
    
    def get_test_batch_feature(self, batch_size = cfg.batch_size):
        '''
        get test images by batch
        args:
            batch size
        return:
            test feature of profile images and front images
        '''
        teX = np.zeros((batch_size, 4096), dtype=np.float32)
        teY = np.zeros((batch_size, cfg.height, cfg.width, 3), dtype=np.float32)
        for i in range(batch_size):
            try:
                teX[i] = self.read_feature(self.f_test)
                teY[i] = self.read_image(self.test_list[i +self.test_index][1])
            except:
                self.test_index = -i
                self.f_test.seek(0)
                teX[i] = self.read_feature(self.f_test)
                teY[i] = self.read_image(self.test_list[i +self.test_index][1])
        self.test_index += batch_size
        return(teX, teY)
        
    def read_image(self, img):
        '''
        read single image and crop to target size
        '''
        img = Image.open(os.path.join(cfg.data_path, img))
        if cfg.crop:
            img = img.crop(self.crop_box)
        return np.array(img, dtype=np.float32)
            
    def read_feature(self, f, dim=4096):
        '''
        read single feature of image with dimension of 4096 from binary file
        '''
        return np.array(struct.unpack(str(dim)+'f', f.read(dim*4)), dtype=np.float32)
        
    def save_images(self, imgs, epoch=0):
        '''
        args:
            imgs: [batch_size, img_height, img_width, img_chanel], image pixels need
            to be normalized between [-1, 1]
        '''
        imgs = imgs.astype('uint8')  # inverse_transform
        img_num = imgs.shape[0]
        test_size = self.test_list.shape[0]
        save_path = cfg.results + '/epoch'+str(epoch)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        for i in range(imgs.shape[0]):
            try:
                Image.fromarray(imgs[i]).save(os.path.join(save_path, 
                    self.test_list[i +self.test_index-img_num][0]))
            except:
                Image.fromarray(imgs[i]).save(os.path.join(save_path, 
                    self.test_list[test_size+i+self.test_index-img_num][0]))


def mergeImgs(images, size):
    h, w = images.shape[1], images.shape[2]
    imgs = np.zeros((h * size[0], w * size[1], 3))
    for idx, image in enumerate(images):
        i = idx % size[1]
        j = idx // size[1]
        imgs[j * h:j * h + h, i * w:i * w + w, :] = image

    return imgs


if __name__ == '__main__':
    def f1():
        '''
        label images with label/session/pose/illuminatio/express
        '''
        l = np.loadtxt('images.txt',dtype='string')
        l = pd.DataFrame(l,columns=['name'])
        l['label'] = 1; l['exp'] = 1; l['pose'] = '051'; l['ill'] = '07'; l['sess'] = '01'
        for i in range(l.shape[0]):
            name = l.iloc[i,0]
            l.iloc[i,1] = int(name[:3])
            l.iloc[i,2] = int(name[7:9])
            l.iloc[i,3] = name[10:13]
            l.iloc[i,4] = name[14:16]
            l.iloc[i,5] = name[4:6]  
        l.to_csv('session01.csv',index=false)
        
    def f2():
        '''
        divide into train set and test set according to setting 1 of MIPE
        '''
        #images = pd.read_csv('session01.csv',dtype='string')
        images = pd.read_csv('session01.csv')
        images = images[images.exp == 1]
        train = images[images.label < 101]
        pose_set1 = [80,130,140,51,50,41,190]
        with open('setting1_train.txt', 'w') as f:
            for pose in pose_set1:
                train_pose = train[train.pose == pose]
                for name in train_pose.name.values:
                    f.write(name+',')
                    f.write(name[:10]+'051_07.jpg\n')
                    f.flush()
        test = images[images.label > 100]
        with open('setting1_test.txt', 'w') as f:
            for pose in pose_set1:
                test_pose = test[test.pose == pose]
                for name in test_pose.name.values:
                    f.write(name+',')
                    f.write(name[:10]+'051_07.jpg\n')
                    f.flush()    
    
    def f2():
        '''
        get the ground true of the test images
        '''
        images = os.listdir('session01_img/')
        for name in images:
            os.system('cp /home/pris/Videos/session01_align/'+name+' session01_img/gt/')
            
    def f3():
        '''
        extract image features by VGG-FACE
        '''
        def read_img(img):
            img = Image.open(os.path.join(cfg.data_path, img))
            img = img.crop((3,3,227,227))
            return np.array(img, dtype=np.float32)
        def inpack(array_img):
            write_temp = ''
            for i in range(array_img.shape[0]):
                for j in array_img[i]:
                     write_temp += struct.pack('f',j)
            return write_temp
        import vgg16
        vgg = vgg16.Vgg16()
        vgg.build()
        profile = tf.placeholder("float", [None, 224, 224, 3])
        fc7_encoder = vgg.forward(profile)
        sess = tf.InteractiveSession()
        sess.run(tf.global_variables_initializer())
        batch = 20
        images = np.loadtxt('session01_test2.txt', dtype='string', delimiter=',')
        with open('session01_test2_feature', 'wb') as f:
            for i in range(images.shape[0] / batch):
                print i
                trX = np.zeros((batch, 224, 224, 3), dtype=np.float32)
                for j in range(batch):
                    trX[j] = read_img(images[i*batch + j][0])
                features = sess.run(fc7_encoder, feed_dict={profile: trX})
                write_temp = inpack(features)
                f.write(write_temp)
        
    
    
    
