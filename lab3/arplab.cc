#include "node.h"
#include <arpa/inet.h> // Para funciones de manejo de endiannes.

// Estructura de una trama Ethernet
struct ethernet_frame_t {

    MACAddress destination;
    MACAddress source;
    uint16_t type; // Protocolo encapsulado en el payload.
    char payload[IP_PAYLOAD_SIZE]; // Carga util 1500 bytes.

} __attribute__ ((packed)); // 

// Estructura de un paquete ARP (Generica)
struct arp_packet_t {

    uint16_t hrd; // Espacio de direcciones de hardware.
    uint16_t prot; // Espacio de direcciones de protocolo.
    uint8_t hrd_len; // Longitud de cada direccion de hardware.
    uint8_t prot_len; // Longitud de cada direccion de protocolo.
    uint16_t op_code; // Codigo de la operacion (REQUEST | REPLY).
    unsigned char s_hrd_addr[HRD_ADDR_SIZE]; // Direccion hardware origen (source).
    unsigned char s_prot_addr[PROT_ADDR_SIZE]; // Direccion protocolo origen (source).
    unsigned char t_hrd_addr[HRD_ADDR_SIZE]; // Direccion hardware destino (target).
    unsigned char t_prot_addr[PROT_ADDR_SIZE]; // Direccion protocolo destino (target).

} __attribute__ ((packed));

// Sinonimos para los nuevos tipos de datos.
typedef struct ethernet_frame_t ethernet_frame;
typedef struct arp_packet_t arp_packet;

int Node::send_to_ip(IPAddress ip, void *data) {

    // Crea una trama Ethernet.
    ethernet_frame frame;

    // Set direccion MAC origen.
    get_my_mac_address(frame.source);

    // Conoce el destino?

    // Busca en la tabla ARP la entrada para esa IP.
    if (memcmp(arp_table[ip[3]], broadcast_addr,  HRD_ADDR_SIZE)) {
    // SI!
        // La MAC se encuentra en la tabla.

        // Copia la MAC destino al encabezado de la trama.
        memcpy(frame.destination, arp_table[ip[3]], HRD_ADDR_SIZE);
        // Define el tipo de protocolo como IPv4 (Bid Endian).
        frame.type = htons(IP_TYPE);
        // Agrega la data a la carga util de la trama.
        memcpy(frame.payload, data, IP_PAYLOAD_SIZE);
        // Envia los datos a la capa fisica.
        send_ethernet_packet(&frame);

        return 0; // Salida exitosa.

    } else {
    // NO!
        // La MAC no se encuentra en la tabla de traduccion.

        // Arma el paquete ARP (REQUEST).
        arp_packet arp;
        // Espacio de direcciones (Hardware y Protocolo).
        arp.hrd = htons(ETHERNET_TYPE);
        arp.prot = htons(IP_TYPE);
        // Longitud de los espacios de direcciones.
        arp.hrd_len = HRD_ADDR_SIZE;
        arp.prot_len = PROT_ADDR_SIZE;
        // Codigo para request.
        arp.op_code = htons(REQUEST_OP_CODE);
        // Direcciones MAC e IP origen.
        get_my_mac_address(arp.s_hrd_addr);
        get_my_ip_address(arp.s_prot_addr);
        // Setea a una direccion de hardware 'neutra'.
        memcpy(arp.t_hrd_addr, broadcast_addr, HRD_ADDR_SIZE);
        // Direccion IP destino.
        memcpy(arp.t_prot_addr, ip, PROT_ADDR_SIZE);
        // Paquete ARP completo.

        // Completa la trama Ethernet.

        // Setea el destino para difusion.
        memcpy(frame.destination, broadcast_addr, HRD_ADDR_SIZE);
        // Ahora el tipo es Address Resolution Protocol (B.E.).
        frame.type = htons(ARP_TYPE);
        // Carga en el payload el paquete ARP.
        memcpy(frame.payload, &arp, IP_PAYLOAD_SIZE);
        // Envia la trama a la capa fisica.
        send_ethernet_packet(&frame);

        return 1; // Debe reintentar luego el envio de data.
    }
}

void Node::receive_ethernet_packet(void *packet) {
    // *packet es un buffer de ETHERFRAME_SIZE bytes.
    // El paquete es un puntero void desconocido.
    // Necesita interpretarlo como un puntero a una trama Ethernet.
    // Crea entonces puntero a una trama casteando.
    ethernet_frame* frame = (ethernet_frame *) packet;
    // Obtiene su propia MACAddress. La necesita en ambos casos.
    MACAddress my_mac;
    get_my_mac_address(my_mac);

    // La carga util es un paquete ARP?
    if (ntohs(frame->type) == ARP_TYPE) {
        // Debe procesarlo.
        // El payload de la trama debe ser interpretado como un paquete ARP.
        // Nuevo puntero casteado a la estructura arp_packet.
        arp_packet* arp = (arp_packet *) frame->payload;
        
        // Comienza el algoritmo de resolucion de direccion.

        // El nodo tiene el tipo de hardware que el paquete ARP indica?
        if (ntohs(arp->hrd) == ETHERNET_TYPE) {
            // Chequeo de longitud de hardware address.
            if (arp->hrd_len == HRD_ADDR_SIZE) { // No necesita manejar endianess porque es un solo Byte.
                // 'Habla' en el protocolo especificado?
                if (ntohs(arp->prot) == IP_TYPE) {
                    // Chequea longitud de protocolo.
                    if (arp->prot_len == PROT_ADDR_SIZE) {
                        int merge_flag = 0; // Bandera en Falso.
                        // Busca la ip en la tabla.
                        if (memcmp(arp_table[arp->s_prot_addr[3]], broadcast_addr, HRD_ADDR_SIZE)) {
                            // La direccion se encuentra en la tabla de traduccion.
                            // Actualiza la MACAddress para esa entrada IPAddress.
                            memcpy(arp_table[arp->s_prot_addr[3]], arp->s_hrd_addr, HRD_ADDR_SIZE);
                            merge_flag = 1;
                        }
                        // Soy direccion IP destino?
                        IPAddress my_ip;
                        get_my_ip_address(my_ip);

                        if (!memcmp(arp->t_prot_addr, my_ip, PROT_ADDR_SIZE)) {
                            // Son iguales las direcciones IP.
                            // 'El paquete era para mi'.
                            if (!merge_flag) {
                                // La tabla de traduccion no tiene datos para esa IP.
                                memcpy(arp_table[arp->s_prot_addr[3]], arp->s_hrd_addr, HRD_ADDR_SIZE);
                                // Setea el valor de la MACAddress para esa entrada IP.
                            }
                            if (ntohs(arp->op_code) == REQUEST_OP_CODE) {
                                // Piden mi MACAddress.
                                // Variables temporales para el swap.
                                MACAddress tmp_hrd_addr;
                                IPAddress tmp_prot_addr;
                                // Swap de los campos de direcciones (MAC e IP) destino y origen.
                                memcpy(tmp_hrd_addr, arp->s_hrd_addr, HRD_ADDR_SIZE);
                                memcpy(tmp_prot_addr, arp->s_prot_addr, PROT_ADDR_SIZE);
                                // Segunda parte del swap.
                                memcpy(arp->s_hrd_addr, my_mac, HRD_ADDR_SIZE);
                                memcpy(arp->s_prot_addr, my_ip, PROT_ADDR_SIZE);
                                // Tercera parte.
                                memcpy(arp->t_hrd_addr, tmp_hrd_addr, HRD_ADDR_SIZE);
                                memcpy(arp->t_prot_addr, tmp_prot_addr, PROT_ADDR_SIZE);
                                // Ahora el paquete responde a un REPLY (Big Endian).
                                arp->op_code = (htons(REPLY_OP_CODE));
                                // Paquete ARP completo.

                                // Arma el paquete Ethernet para enviarlo.
                                // Setea las direcciones MAC destino y origen (nuevas).
                                memcpy(frame->destination, arp->t_hrd_addr, HRD_ADDR_SIZE);
                                memcpy(frame->source, arp->s_hrd_addr, HRD_ADDR_SIZE);
                                // La trama envia un paquete ARP.
                                frame->type = htons(ARP_TYPE);
                                // El payload de la trama es el paquete creado anteriormente.
                                memcpy(frame->payload, arp, IP_PAYLOAD_SIZE);

                                // Se envia la trama a la capa fisica.
                                send_ethernet_packet(frame);
                            }
                        }
                    }
                }
            }
        }
    } else if (ntohs(frame->type) == IP_TYPE) {
        // Es un paquete de datos.
        // Es para mi?
        if (!memcmp(my_mac, frame->destination, HRD_ADDR_SIZE)) {
            // Se pasa el paquete a la capa de red.
            receive_ip_packet(frame->payload);
        }
    }
}

/*
 * Constructor de la clase. Poner inicialización aquí.
 */
Node::Node()
{
    timer = NULL;
    /* Inicializacion de la tabla de traduccion.
     * En un principio se setea con una direccion valida 'neutra'.
     * Elegimos broadcast y nos aseguramos que no exista un host
     * con esa direccion MAC.
     * Si en el indice de la tabla, la direccion MAC es broadcast
     * equivale a decir que no hay una entrada para esa IP.
     */
    for (unsigned int i = 0; i != ADDRESS_SPACE; i++) {
        memcpy(arp_table[i], broadcast_addr,  HRD_ADDR_SIZE);
    }

    for (unsigned int i = 0; i != AMOUNT_OF_CLIENTS; ++i) {
        seen[i] = 0;
    }
}
