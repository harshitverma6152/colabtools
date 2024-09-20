import java.util.Scanner;
import java.util.Arrays;

class ArrayTest {
    int arr[]; 

    
    public ArrayTest(int size) {
        arr = new int[size];
        Scanner sc = new Scanner(System.in);
        System.out.println("Enter " + size + " elements for the array (comma-separated or space-separated):");
        for (int i = 0; i < size; i++) {
            arr[i] = sc.nextInt(); 
        }
    }

    
    public void avgAtOddIndex() {
        int sum = 0, count = 0;
        for (int i = 1; i < arr.length; i += 2) { 
            sum += arr[i];
            count++;
        }
        double avg = (double) sum / count;
        System.out.println("Average of elements at odd indices: " + avg);
    }

    
    public int[] factorialOfElements() {
        int[] factorials = new int[arr.length];
        for (int i = 0; i < arr.length; i++) {
            factorials[i] = factorial(arr[i]);
        }
        return factorials;
    }

    // Helper method to calculate factorial
    private int factorial(int num) {
        int fact = 1;
        for (int i = 2; i <= num; i++) {
            fact *= i;
        }
        return fact;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        
        System.out.print("Enter the size of the array: ");
        int size = sc.nextInt();

        
        ArrayTest arrayTest = new ArrayTest(size);
        
        
        System.out.println("Input array: " + Arrays.toString(arrayTest.arr));

        
        arrayTest.avgAtOddIndex();

        
        int[] factorials = arrayTest.factorialOfElements();
        System.out.println("Factorials of array elements: " + Arrays.toString(factorials));
    }
}
