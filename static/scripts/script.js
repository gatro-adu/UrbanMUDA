const wsConnections = {};
const createdTasks = new Set();
const chatBubblesByTaskId = {}; // 记录每个主任务ID对应的气泡DOM
const systemBubblesByTaskId = {}; // 记录系统回复气泡

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("chat-input");

  input.addEventListener("keydown", function (e) {
    // Shift + Enter 换行，单独 Enter 发送
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault(); // 阻止默认换行行为
      sendChatCommand();
    }
  });
});

async function sendChatCommand() {
  const input = document.getElementById("chat-input");
  const config = document.getElementById("config");
  let command = input.value.trim();
  let config_text = config.value.trim();
  // 设置默认测试指令
  if (!command) {
    command = "在杨梅分局西侧10米部署红方两架四旋翼无人机; 然后在龙龟西南侧呈正三角队形部署蓝军3辆155mm自行火炮";
  }

  // 创建新的聊天气泡作为主任务记录
  const taskBubble = appendChatMessage("user", command);
  input.value = "";

  // 为系统回复创建初始气泡
  const systemBubble = appendChatMessage("system", "处理中...\n");

  function isValidJson(str) {
    try {
        JSON.parse(str);
        return true;
    } catch {
        return false;
    }
  }

  let configs_raw = config_text.split('\n').filter(cmd => cmd.trim() !== "");
  let configs_send = [];
  for (let i = 0; i < configs_raw.length; i++) {
    if (!isValidJson(configs_raw[i])) {
      if (configs_raw[i] != "") {
        console.error("请输入合法的 JSON！");
        return;
      }
    } else {
      configs_send.push(JSON.parse(configs_raw[i]));
    }
  }

  const commands = command.split('\n').filter(cmd => cmd.trim() !== "");
  console.log(configs_send);
  console.log(commands);
  const inputData = {
    "order_list": commands,
    "configs": configs_send,
  };

  const res = await fetch('/run_test_agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(inputData)
  });

  const data = await res.json();
  connectToParentTask(data.task_id, data.task_name, taskBubble, systemBubble);
}

function appendChatMessage(sender, content) {
  const history = document.getElementById("chat-history");
  const msgWrapper = document.createElement("div");
  msgWrapper.className = `chat-message ${sender === 'user' ? 'user' : 'system'}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = content;

  msgWrapper.appendChild(bubble);
  history.appendChild(msgWrapper);

  history.scrollTop = history.scrollHeight;
  return bubble; // 返回该气泡 DOM，用于后续追加内容
}

function connectToParentTask(taskId, taskName, userBubbleDiv, systemBubbleDiv) {
  // 记录气泡关联
  chatBubblesByTaskId[taskId] = userBubbleDiv;
  systemBubblesByTaskId[taskId] = systemBubbleDiv;

  // 创建WebSocket连接
  const ws = new WebSocket(`ws://${location.host}/ws?task_id=${taskId}&task_name=${taskName}`);
  wsConnections[taskId] = ws;
  
  ws.onmessage = event => {
    try {
      const data_json = JSON.parse(event.data);

      if (data_json.type === "init") {
        // 为子任务创建任务窗口
        if (data_json.task_id !== taskId) {
          createTaskWindow(data_json.task_id, data_json.task_name);
        }
      } else if (data_json.type === "progress") {
        console.log(`任务 ${data_json.task_name} 进度: ${data_json.progress}%`);
        // 更新系统气泡显示进度
        const systemBubble = systemBubblesByTaskId[taskId];
        if (systemBubble) {
          systemBubble.textContent += `处理中... \n(${data_json.progress}%)` + '\n';
        }
      } else if (data_json.type === "done") {
        console.log(`任务 ${data_json.task_name} 完成`);
        
        // 更新主任务的系统气泡
        const systemBubble = systemBubblesByTaskId[taskId];
        if (systemBubble) {
          systemBubble.textContent += `✅ 任务「${data_json.task_name}」已完成` + '\n';
        }

        // 在聊天历史中添加完成通知
        const doneNotice = document.createElement("div");
        doneNotice.textContent = `✅ 任务「${data_json.task_name}」已完成`;
        doneNotice.style.textAlign = "center";
        doneNotice.style.color = "#555";
        doneNotice.style.margin = "10px 0";
        document.getElementById("chat-history").appendChild(doneNotice);
      }
    } catch (e) { }

    // 处理常规消息
    if (!event.data.includes('❤')) {
      const cleanText = event.data.replace(/temp/g, "\n").trim();
      
      // 主任务输出显示在系统气泡中
      const systemBubble = systemBubblesByTaskId[taskId];
      if (systemBubble) {
        systemBubble.textContent += cleanText + '\n';
      }
    }
  };

  ws.onclose = () => {
    console.log(`WebSocket for task ${taskId} closed`);
    delete wsConnections[taskId];
  };
}

const tasksContainer = document.getElementById('tasks-container');
let autoScrollContainer = true; // 默认开启自动滚动
let userScrolledUpContainer = false; // 标记用户是否手动向上滚动

tasksContainer.addEventListener('scroll', function() {
  // 检查用户是否滚动到底部
  const isAtBottom = tasksContainer.scrollHeight - tasksContainer.scrollTop === tasksContainer.clientHeight;
  
  if (isAtBottom) {
    // 如果用户滚动到底部，恢复自动滚动
    autoScrollContainer = true;
    userScrolledUpContainer = false;
  } else if (!userScrolledUpContainer && tasksContainer.scrollTop < output.scrollHeight - tasksContainer.clientHeight) {
    // 如果用户向上滚动且不是在最底部，暂停自动滚动
    autoScrollContainer = false;
    userScrolledUpContainer = true;
  }
});
  
function createTaskWindow(taskId, taskName) {
  if (createdTasks.has(taskId)) return;
  createdTasks.add(taskId);

  const container = document.getElementById('tasks-container');
  const taskDiv = document.createElement('div');
  taskDiv.className = 'task-box';
  taskDiv.id = taskId;

  taskDiv.innerHTML = `
    <div class="task-header">${taskName} <span class="task-status status-running">运行中</span></div>
    <pre id="output-${taskId}"></pre>
  `;

  container.appendChild(taskDiv);

  if (autoScrollContainer) {
    tasksContainer.scrollTo({
      top: tasksContainer.scrollHeight,
      behavior: 'smooth'
    });
  }

  let autoScroll = true;
  let userScrolledUp = false;

  // 监听滚动事件
  taskDiv.addEventListener('scroll', function() {
    // 检查用户是否滚动到底部
    const isAtBottom = taskDiv.scrollHeight - taskDiv.scrollTop === taskDiv.clientHeight;
    
    if (isAtBottom) {
      // 如果用户滚动到底部，恢复自动滚动
      autoScroll = true;
      userScrolledUp = false;
    } else if (!userScrolledUp && taskDiv.scrollTop < output.scrollHeight - taskDiv.clientHeight) {
      // 如果用户向上滚动且不是在最底部，暂停自动滚动
      autoScroll = false;
      userScrolledUp = true;
    }
  });


  const output = taskDiv.querySelector('pre');
  const statusElement = taskDiv.querySelector('.task-status');

  const ws = new WebSocket(`ws://${location.host}/ws?task_id=${taskId}&task_name=${taskName}`);
  wsConnections[taskId] = ws;
  
  ws.onmessage = event => {
    try {
      const data_json = JSON.parse(event.data);

      if (data_json.type === "done") {
        statusElement.textContent = "已完成";
        statusElement.className = "task-status status-done";
      }
    } catch (e) { }

    if (!event.data.includes('❤')) {
      const cleanText = event.data.replace(/temp/g, "\n").trim();
      output.textContent += cleanText + "\n";
    }

    // 只有在autoScroll为true时才自动滚动
    if (autoScroll) {
      taskDiv.scrollTop = taskDiv.scrollHeight;
    }
  };

  ws.onclose = () => {
    console.log(`WebSocket for task ${taskId} closed`);
    delete wsConnections[taskId];
  };
}
