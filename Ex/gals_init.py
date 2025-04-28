# %%
import matplotlib.pyplot as plt
import cv2

# %%


# %%


# %%

# читаем картинку
img = cv2.imread('/home/user/PycharmProjects/cv/bb_falder/r142.jpg')
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# разрешение изображения
dh, dw, _ = img.shape

# читаем тхт с разметкой
fl = open('/home/user/PycharmProjects/cv/bb_falder/r142.txt', 'r')
data = fl.readlines()
fl.close()


# %% [markdown]
# У нас в тхт количесство строк равняется количеству объектов, поэтому ниже в цикле читаем по строке и выводим по 1 объекту

# %%
for dt in data:

    # класс, х, у, ширина , высота
    cls, x, y, w, h = dt.split(' ')
            
    nx = int(float(x)*dw)
    ny = int(float(y)*dh)
    nw = int(float(w)*dw/2)
    nh = int(float(h)*dh/2)
            
    cv2.rectangle(img, (nx-nw,ny-nh), (nx+nw,ny+nh), (0,0,255), 1)
            
plt.imshow(img)


# %%


# %%


# %%


# %%


# %%


# %%


# %%


# %%



