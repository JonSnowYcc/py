from jqdatasdk import *
auth('18351936006', 'Ycc940529')




if __name__ == '__main__':
    # 查询当日剩余可调用数据条数
    count = get_query_count()
    print(count)

