import request from "../utils/request";

export const detectSingleImage = (data) => {
  return request({
    url: "/detection/single",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

export const getDetectionHistory = (params) => {
  return request({
    url: "/detection/history",
    method: "get",
    params,
  });
};

export const getDetectionDetail = (id) => {
  return request({
    url: `/detection/detail/${id}`,
    method: "get",
  });
};

export const getTargetList = () => {
  return request({
    url: "/targets/list",
    method: "get",
  });
};

export const detectFrame = (data) => {
  return request({
    url: '/detection/camera/detect',
    method: 'post',
    data,
  });
};