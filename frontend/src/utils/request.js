import axios from "axios";

const service = axios.create({
  baseURL: "http://localhost:8001",
  // baseURL: "http://43.138.252.29:8001",
  timeout: 10000,
});

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // // 可在此处添加 token 等
    // config.headers.Authorization = "Bearer xxx";
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
service.interceptors.response.use(
  (response) => response.data, // 直接返回数据部分
  (error) => Promise.reject(error)
);

export default service;
