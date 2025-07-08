<template>
  <div class="home-container">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="logo">智慧课堂系统</div>
      <nav class="nav-menu">
        <RouterLink to="/" exact-active-class="active">首页</RouterLink>
        <RouterLink to="/realVideo" active-class="active">实时监控</RouterLink>
        <RouterLink to="/coordinate" active-class="active">坐标对齐</RouterLink>
        <RouterLink to="/about" active-class="active">课程中心</RouterLink>
      </nav>
      <div class="user-actions">
        <button class="notification-btn">🔔</button>
        <div class="user-info">
          <span class="avatar">👤</span>
          <a href="#">张老师</a>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <RouterView/>
    <!-- 页脚 -->
    <footer class="footer">
      <p>“瞳心” 智慧课堂系统 © 2025 版权所有 | 教育科技赋能未来</p>
      <div class="footer-links">
        <a href="#">关于我们</a>
        <a href="#">帮助中心</a>
        <a href="#">隐私政策</a>
        <a href="#">联系我们</a>
      </div>
    </footer>
  </div>
</template>

<script>
// import {userStore} from "@/stores/userStore.js";

export default {
  data(){
    return {
      active:'/',
    }
  },
  // // 组件加载前检查是否登录
  // beforeCreate() {
  //   console.log(userStore().is_login);
  //   if (!userStore().getLoginStatus){
  //     this.$router.push('/login')
  //   }
  // }
}

</script>


<style scoped>
.home-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f7fa;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* 顶部导航栏样式 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 2rem;
  height: 60px;
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 1.2rem;
  font-weight: bold;
  color: #409EFF;
}

.nav-menu {
  display: flex;
  gap: 2rem;
}

.nav-menu a {
  text-decoration: none;
  color: #606266;
  padding: 0.5rem 0;
  transition: color 0.3s;
}

.nav-menu a.active,
.nav-menu a:hover {
  color: #409EFF;
  border-bottom: 2px solid #409EFF;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.notification-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #606266;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.avatar {
  background-color: #e6f7ff;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 页脚样式 */
.footer {
  text-align: center;
  padding: 1.5rem;
  background-color: white;
  color: #909399;
  font-size: 0.9rem;
  border-top: 1px solid #ebeef5;
}

.footer-links {
  margin-top: 0.5rem;
}

.footer-links a {
  color: #606266;
  text-decoration: none;
  margin: 0 0.8rem;
  transition: color 0.3s;
}

.footer-links a:hover {
  color: #409EFF;
}
</style>
