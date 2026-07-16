/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // 输出 standalone 产物（.next/standalone），用于轻量 Docker 部署
  output: "standalone",
  // 如需自定义镜像域名下的资源前缀可在此配置，本地部署无需改动
};

export default nextConfig;
