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
    """Class for loading data.
    
    This is a class for loading data (e.g. image) to model. Train image 
    and test image can be obtained by function "get_train" and 
    function "get_test_batch" respectively.
    
    Args:
        batch_size (int): size of every train batch
        train_shuffle (bool): whether to shuffle train set.
        
    """
    def __init__(self, batch_size = 20, train_shuffle = True):
        self.batch_size = batch_size
        self.profile = np.loadtxt(cfg.profile_list, dtype='string', delimiter=',')
        self.front = np.loadtxt(cfg.front_list, dtype='string', delimiter=',')
        
        if(train_shuffle): 
            np.random.shuffle(self.profile)
            np.random.shuffle(self.front)
                         
        self.test_list = np.loadtxt(cfg.test_list, dtype='string',delimiter=',') #
        self.test_index = 0
        
        # Crop Box: left, upper, right, lower
        self.crop_box = [(cfg.ori_width - cfg.width) / 2, (cfg.ori_height - cfg.height) / 2,
                        (cfg.ori_width + cfg.width) / 2, (cfg.ori_height + cfg.height) / 2]         
        assert Image.open(os.path.join(cfg.profile_path, self.profile[0])).size == \
               (cfg.ori_width, cfg.ori_height)
    
    def get_train(self):
        """Get train images by Feeding
        
        Train images will be horizontal-flipped and center-cropped randomly.
        
        return:
            profile (tf.tensor): profile of identity A
            front (tf.tensor): front face of identity B
        """
        with tf.name_scope('data_feed'):
            profile_list = [cfg.profile_path+'/'+img for img in self.profile]
            front_list = [cfg.front_path+'/'+img for img in self.front]
            profile_files = tf.train.string_input_producer(profile_list, shuffle=False) #
            front_files = tf.train.string_input_producer(front_list, shuffle=False) #
            
            _, profile_value = tf.WholeFileReader().read(profile_files)
            profile_value = tf.image.decode_jpeg(profile_value, channels=cfg.channel)
            _, front_value = tf.WholeFileReader().read(front_files)
            front_value = tf.image.decode_jpeg(front_value, channels=cfg.channel) 
            
            # Flip and crop image
            lf_profile_value = tf.image.random_flip_left_right(profile_value)
            crop_profile_value = tf.random_crop(lf_profile_value, [cfg.height, cfg.width, cfg.channel])
            # Args: [image, offset_height, offset_width, target_height, target_width]
            crop_front_value = tf.image.crop_to_bounding_box(front_value, 
                                                            (cfg.ori_height-cfg.height)/2, 
                                                            (cfg.ori_width-cfg.width)/2, 
                                                            cfg.height, cfg.width)
            profile,front = tf.train.shuffle_batch([crop_profile_value,crop_front_value],
                                                  batch_size=self.batch_size,
                                                  num_threads=8,
                                                  capacity=32 * self.batch_size,
                                                  min_after_dequeue=self.batch_size * 16,
                                                  allow_smaller_final_batch=False)
            return tf.cast(profile, tf.float32, 'profile'), tf.cast(front, tf.float32, 'front')
        
    def get_train_batch(self):
        """Get train images by preload
        
        return:
            trX: training profile images
            trY: training front images
        """
        trX = np.zeros((self.batch_size, cfg.height, cfg.width, cfg.channel), dtype=np.float32)
        trY = np.zeros((self.batch_size, cfg.height, cfg.width, cfg.channel), dtype=np.float32)
        for i in range(self.batch_size):
            try:
                trX[i] = self.read_image(cfg.profile_path+'/'+self.profile[i + self.train_index], flip=True)
                trY[i] = self.read_image(cfg.front_path+'/'+self.front[i + self.train_index], flip=True)
            except:
                self.train_index = -i
                trX[i] = self.read_image(cfg.profile_path+'/'+self.profile[i +self.train_index], flip=True)
                trY[i] = self.read_image(cfg.front_path+'/'+self.front[i +self.train_index], flip=True)
        self.train_index += self.batch_size
        return trX, trY
        
    def get_test_batch(self, batch_size = cfg.batch_size):
        """Get test images by batch
        
        args:
            batch_size: size of test scratch
        return:
            teX: testing profile images
            teY: testing front images, same as profile images
        """
        teX = np.zeros((batch_size, cfg.height, cfg.width, cfg.channel), dtype=np.float32)
        teY = np.zeros((batch_size, cfg.height, cfg.width, cfg.channel), dtype=np.float32)
        for i in range(batch_size):
            try:
                teX[i] = self.read_image(cfg.test_path+'/'+self.test_list[i +self.test_index])
                teY[i] = self.read_image(cfg.test_path+'/'+self.test_list[i +self.test_index])
            except:
                print("Test Loop at %d!" % self.test_index)
                self.test_index = -i
                teX[i] = self.read_image(cfg.test_path+'/'+self.test_list[i +self.test_index])
                teY[i] = self.read_image(cfg.test_path+'/'+self.test_list[i +self.test_index])
        self.test_index += batch_size
        return teX, teY

    def read_image(self, img, flip=False):
        """Read image
        
        Read a image from image path, and crop to target size
        and random flip horizontally
        
        args:
            img: image path
        return:
            img: data matrix from image
        """
        img = Image.open(img)
        if(img.mode=='L' and cfg.channel == 3):
            img = img.convert('RGB')
        if flip and np.random.random() > 0.5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if cfg.crop:
            img = img.crop(self.crop_box)
        img = np.array(img, dtype=np.float32)
        if(cfg.channel == 1):
            img = np.expand_dims(img, axis=2)
        return img
        
    def save_images(self, imgs, epoch=0):
        """Save images
     
        args:
            imgs: images in shape of [BatchSize, Weight, Height, Channel], must be normalized to [0,255]
            epoch: epoch number
        """
        imgs = imgs.astype('uint8')  # inverse_transform
        if(cfg.channel == 1):
            imgs = imgs[:,:,:,0]
        img_num = imgs.shape[0]
        test_size = self.test_list.shape[0]
        save_path = cfg.results + '/epoch'+str(epoch)
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        for i in range(imgs.shape[0]):
            try:
                img_name = self.test_list[i + self.test_index - img_num].split('/')[-1]
            except:
                img_name = self.test_list[test_size + i + self.test_index - img_num].split('/')[-1]
            Image.fromarray(imgs[i]).save(os.path.join(save_path, img_name))
            
    def save_train(self, imgs):
        """Save images in training process
        
        args:
            imgs: images in shape of [BatchSize, Weight, Height, Channel], must be normalized to [0,255]
        """
        imgs = imgs.astype('uint8')  # inverse_transform
        img_num = imgs.shape[0]
        if(cfg.channel == 1):
            imgs = imgs[:,:,:,0]
        save_path = 'train_imgs'
        if not os.path.exists(save_path):
            os.mkdir(save_path)
        for i in range(imgs.shape[0]):
            Image.fromarray(imgs[i]).save(os.path.join(save_path, 'imgs_' + str(i) + '.jpg'))
            
if __name__ == '__main__':
    def f1():
        """
        label images with label/session/pose/illuminatio/express
        """
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
        """
        divide into train set and test set according to setting 1 of MIPE
        """
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
        """
        get the ground true of the test images
        """
        images = os.listdir('session01_img/')
        for name in images:
            os.system('cp /home/pris/Videos/session01_align/'+name+' session01_img/gt/')
            
    def f3():
        """
        extract image features by VGG-FACE
        """
        def read_img(img):
            img = Image.open(os.path.join('/home/prisVideos/session01_align', img))
            img = img.crop((13,13,237,237))
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
        batch = 10
        images = np.loadtxt('mpie/session01_train.txt', dtype='string', delimiter=',')
        with open('mpie/session01_test3_feature', 'wb') as f:
            for i in range(images.shape[0] / batch):
                print i
                trX = np.zeros((batch, 224, 224, 3), dtype=np.float32)
                for j in range(batch):
                    trX[j] = read_img(images[i*batch + j][0])
                features = sess.run(fc7_encoder, feed_dict={profile: trX})
                write_temp = inpack(features)
                f.write(write_temp)
        
    
    
    
