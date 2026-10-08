# 基本定义
list_A=["python","httpd","tomcat"]
print(type(list_A))
print(list_A)

# 嵌套列表
list_B=[10,3.14,"python",["httpd","tomcat"]]
print(list_B)

# 怎么去用列表
print(list_A[0])

#以循环的方式定义列表数据
list_C=[i for i in range(1,10)]
print("-------以循环的方式定义列表数据1-10-------")
print(list_C)
