import request from "../utils/request";

// 单图检测接口
export const detectSingleImage = (data) => {
  return request({
    url: "/detection/single",
    method: "post",
    data,
  });
};

// 批量图片检测
export const detectBatchImages = (data) => {
  return request({
    url: "/detection/batch",
    method: "post",
    data,
  });
};

// 视频文件检测
export const detectVideo = (data) => {
  return request({
    url: "/detection/video",
    method: "post",
    data,
    timeout: 0,
  });
};

// 单帧检测（摄像头实时预览）
export const detectFrame = (data) => {
  return request({
    url: "/detection/frame",
    method: "post",
    data,
  });
};

// 获取检测历史
export const getDetectionHistory = (params) => {
  return request({
    url: "/detection/history",
    method: "get",
    params,
  });
};

// 获取检测详情
export const getDetectionDetail = (id) => {
  return request({
    url: `/detection/detail/${id}`,
    method: "get",
  });
};

// 删除检测记录
export const deleteDetection = (id) => {
  return request({
    url: `/detection/${id}`,
    method: "delete",
  });
};

// 获取水果库列表
export const getTargetList = () => {
  return request({
    url: "/detection/targets/list",
    method: "get",
  });
};
