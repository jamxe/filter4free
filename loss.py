import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms


class ChiSquareLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.bias = 1e-10
        self.bins = 256

    def forward(self, hist1, hist2):
        # batch_size,channel,W,H
        assert hist1.size() == hist2.size(), "Histograms must have the same shape"
        total_loss = 0.
        batch_size = hist1.size()[0]
        hist1 = hist1 * 255
        hist2 = hist2 * 255
        for i in range(batch_size):
            r1 = torch.histc(hist1[i, 0, :, :], bins=self.bins, min=0, max=256)
            g1 = torch.histc(hist1[i, 1, :, :], bins=self.bins, min=0, max=256)
            b1 = torch.histc(hist1[i, 2, :, :], bins=self.bins, min=0, max=256)
            h1 = torch.cat((r1, g1, b1), dim=0).unsqueeze(0)
            h1 = h1 / h1.sum()

            # print(h1.shape)
            r2 = torch.histc(hist2[i, 0, :, :], bins=self.bins, min=0, max=256)
            g2 = torch.histc(hist2[i, 1, :, :], bins=self.bins, min=0, max=256)
            b2 = torch.histc(hist2[i, 2, :, :], bins=self.bins, min=0, max=256)
            h2 = torch.cat((r2, g2, b2), dim=0).unsqueeze(0)
            h2 = h2 / h2.sum()

            # print(h2.shape)
            chi_squared = torch.sum((h1 - h2) ** 2 / (h1 + h2 + self.bias))
            total_loss = total_loss + chi_squared
            # You can optionally normalize the chi_squared value by the number of bins.
        chi_squared = total_loss / batch_size
        chi_squared.requires_grad = True
        return chi_squared


class HistogramLoss(nn.Module):
    def __init__(self, num_bins=256, margin=1):
        super(HistogramLoss, self).__init__()
        self.num_bins = num_bins
        self.margin = margin

    def forward(self, x, y):
        hist_x = self.compute_histogram(x)
        hist_y = self.compute_histogram(y)
        loss = self.histogram_loss(hist_x, hist_y)

        return loss

    def compute_histogram(self, img):
        hist = []
        for i in range(img.shape[0]):  # Iterate over channels
            hist_channel = torch.histc(img[i, :, :, :] * 255, bins=self.num_bins, min=0, max=255)
            hist_channel = hist_channel / torch.sum(hist_channel)  # Normalize histogram
            hist.append(hist_channel)
        hist = torch.stack(hist, dim=1)
        return hist

    def histogram_loss(self, hist_x, hist_y):
        loss = torch.sum(torch.sqrt(hist_x) - torch.sqrt(hist_y)) ** 2
        loss = torch.clamp(loss, min=0.0, max=self.margin)
        return loss


class EMDLoss(nn.Module):
    def __init__(self):
        super(EMDLoss, self).__init__()
        self.num_bins = 256
        self.scalar = 1

    def compute_histogram(self, img):
        hist = []
        for i in range(img.shape[0]):  # Iterate over channels
            hist_channel = torch.histc(img[i, :, :, :] * 255, bins=self.num_bins, min=0, max=255)
            hist_channel = hist_channel / torch.sum(hist_channel)  # Normalize histogram
            hist.append(hist_channel)
        hist = torch.stack(hist, dim=1)
        return hist

    def forward(self,im1, im2):
        hist_dist1 = self.compute_histogram(im1)
        hist_dist2 = self.compute_histogram(im2)
        # 计算两个分布的累积分布函数（CDF）
        hist_dist1_cumsum = torch.cumsum(hist_dist1, dim=0)
        hist_dist2_cumsum = torch.cumsum(hist_dist2, dim=0)
        # 计算EMD
        emd_loss = torch.norm(hist_dist1_cumsum - hist_dist2_cumsum, p=1,dim=0)
        # 对每个批次每个通道求平均损失
        total_loss = torch.sum(emd_loss)/hist_dist2.shape[0]*self.scalar/3

        # 在channel、w和h上求和，得到每个批次的MSE损失
        # mse_loss = torch.mean((im1 - im2) ** 2, dim=(1, 2, 3))
        # total_loss = mse_loss+emd_loss
        total_loss.requires_grad = True
        return total_loss



if __name__ == '__main__':
    # 创建两个示例直方图（这里使用随机数据，实际应用中需要根据你的需求计算直方图）
    # im1 = torch.rand((20, 3, 512, 512))  # 10 bins
    # im2 = torch.rand((20, 3, 512, 512))
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    im1 = transform(Image.open('/Users/maoyufeng/Downloads/IMG_29401.JPG')).unsqueeze(0)
    im2 = transform(Image.open('/Users/maoyufeng/slash/dataset/色罩/org/1.jpg')).unsqueeze(0)
    # # 创建损失函数实例
    loss_fn = EMDLoss()
    # # 0.00014203631144482642
    # # 计算Chi-Square距离
    loss = loss_fn(im1, im2)
    print("Chi-Square Loss:", loss.item())