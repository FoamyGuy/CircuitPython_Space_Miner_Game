digit_map = ["p", "a", "w",
             "m", "c", "x",
             "o", "i", "n", "v"]

alphabet = "abcdefghijklmnopqrstuvwxyz"
alphabet = ''.join(reversed(alphabet))

for i in range(9000):
    number_str = str(i)
    output_str = ""
    #print(number_str)
    sum = 0
    for char in number_str:
        sum += int(char)
        output_str += digit_map[int(char)]

    #print(i%26)
    prefix = alphabet[i%26]
    suffix = alphabet[sum%26]
    output_str = f"{prefix}{output_str}{suffix}"
    print(output_str)
    if len(output_str) > 5:
        print(i)
        break

