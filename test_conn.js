setTimeout(function() {
    console.log("[*] ===== 网络连通性测试 =====");

    Java.perform(function() {
        var Thread = Java.use('java.lang.Thread');
        var Runnable = Java.use('java.lang.Runnable');

        // 测试多个目标地址
        var targets = [
            "10.0.2.2",
            "172.25.224.1",
            "172.16.28.43",
            "127.0.0.1"
        ];

        var port = 8888;

        targets.forEach(function(ip) {
            Java.scheduleOnMainThread(Java.registerClass({
                name: 'com.test.Connect' + ip.replace(/\./g, '_'),
                implements: [Runnable],
                methods: {
                    run: function() {
                        testConnection(ip, port);
                    }
                }
            }).$new());
        });

        function testConnection(ip, port) {
            try {
                var Socket = Java.use('java.net.Socket');
                var socket = Socket.$new();
                socket.connect(
                    Java.use('java.net.InetSocketAddress').$new(ip, port),
                    3000
                );
                socket.close();
                console.log("[✅] " + ip + ":" + port + " → 连通！");
            } catch(e) {
                console.log("[❌] " + ip + ":" + port + " → 失败: " + e.message);
            }
        }

        // 同时测试 HTTP 请求
        setTimeout(function() {
            targets.forEach(function(ip) {
                try {
                    var URL = Java.use('java.net.URL');
                    var url = URL.$new("http://" + ip + ":" + port + "/");
                    var conn = url.openConnection();
                    conn.setConnectTimeout(3000);
                    conn.setReadTimeout(3000);
                    var code = conn.getResponseCode();
                    console.log("[✅] HTTP " + ip + ":" + port + " → 响应码=" + code);
                } catch(e) {
                    console.log("[❌] HTTP " + ip + ":" + port + " → " + e.message.substring(0, 80));
                }
            });
        }, 2000);
    });
}, 500);
